# Histórico — governança de armazenamento, auditoria e limpeza de branches (11–12/11/2026)

Registro de continuidade das tarefas executadas em 11 e 12/11/2026. Este documento é versionado de propósito: os logs operacionais detalhados ficaram em `.workspace/`, que é local e **não** sincroniza entre estações. O que precisa sobreviver em qualquer clone está aqui.

As regras atuais de [AGENTS.md](../../AGENTS.md) e o estado corrente em [docs/contexto/ESTADO-ATUAL.md](../contexto/ESTADO-ATUAL.md) prevalecem sobre este registro. Este documento não autoriza produção, publicação, mídia, deploy nem nova fatia de TEMPORAL-02.

## Integrações na main

Commits desta sessão, todos exclusivamente documentais e de governança — nenhum altera código, `platform/`, `orchestration/` ou CI:

| Commit | Assunto |
| --- | --- |
| `c50dc86` | contexto com o BeatPlan v1 integrado |
| `9908f3b` | regra permanente de armazenamento na raiz do projeto |
| `79fd5da` | segurança de worktrees sob a convenção `.workspace/` |
| `ed7e8f1` | contexto com a regra de armazenamento e a auditoria de branches |
| `3c44ae4` | registro da limpeza de 14 branches remotas no contexto |

Integrações técnicas anteriores que esta sessão revisou e registrou, sem reimplementar:

| Commit | Assunto |
| --- | --- |
| `616fd24` | ratificação da fatia Workflow de TEMPORAL-02 (escopo estrito de `f584210`) |
| `d5761b1` | merge do BeatPlan v1 interno, a partir da reconciliação `7d919fc` |

Commits de **outra estação**, recebidos por `git pull` em 12/11 e aqui apenas registrados, não produzidos por esta sessão: `2e663e3`, `040e290`, `b590769`, `b7ed1d9`, `0ac4bde`, `b179da6` (piloto local R002 de vídeo sem áudio, em `tools/`); `f69fb08`, `91721a3`, `63d04d5`, `5376890`, `667f3d3` (execução local de TEMPORAL-02 com cliente, Worker, CLIs, replay formal e gate Elephant–Goldfish); e `2c40967` (mudança da raiz de armazenamento para caminho literal).

## Evolução da regra de armazenamento

Três redações sucessivas, com a substância preservada:

1. **11/11 — raiz `C:/Marketing`.** Regra permanente estabelecida pelo titular: nenhum artefato do projeto fora da raiz; isolamento e auxiliares somente em `.workspace/` com seis subdiretórios por tarefa (`worktrees`, `clones`, `archives`, `logs`, `tmp`, `tools`); validação de contenção antes de criar arquivo; `.gitignore` versionado não alterado para isso; `.workspace/` ignorada por `.git/info/exclude`; limpeza e handoff obrigatórios. Registrada em `9908f3b`.
2. **11/11 — caminho literal `C:/Repos/marcasalao-marketing`** (`2c40967`, outra estação). Revogou `C:/Marketing` e passou a proibi-lo. Essa redação descreve o layout de uma estação específica: aplicada em outra, proíbe o próprio diretório onde o checkout existe. Nesta máquina `C:/Repos` não existe e `.workspace/worktrees/` não continha a worktree `r001-reconcilia` citada no texto.
3. **12/11 — redação portável.** A raiz passa a ser **o próprio checkout principal**: `<RAIZ>` = `git rev-parse --show-toplevel` daquela estação. A proibição é estrutural (qualquer diretório fora de `<RAIZ>`), e um caminho que seja a própria raiz nunca é proibido. Instâncias conhecidas são ilustrativas, não exaustivas.

**O invariante são os arquivos, não o caminho.** O repositório existe em mais de um computador e pode ser aberto por IDEs diferentes, cada um com sua pasta local. O que precisa estar idêntico e atualizado em todas as estações são os arquivos versionados, alinhados por Git: `fetch`/`pull --ff-only` antes de trabalhar, commit e push do que for permanente ao terminar, nunca cópia manual de pastas nem sincronizador de nuvem sobre o checkout, e sem padronizar caminhos entre máquinas. `.workspace/` não sincroniza; evidência que precise viajar deve ser versionada. Divergência entre estações é conflito de conteúdo, não de caminho.

**Nenhum repositório foi realocado.** `C:/Repos` não foi criado nesta máquina. A decisão de manter `C:/Marketing` aqui foi explícita do titular, e o documento recebido do remoto não foi tratado como autorização para mudar a raiz.

A redação portável e o princípio do invariante estão na branch `codex/corrige-contexto-raiz-portavel` (commits `1d731cf` e `83eb4e5`), **publicada e ainda não integrada na main**, aguardando alinhamento com a outra estação.

## Segurança de worktrees

Orientação aproveitável de uma branch obsoleta, reescrita sob `.workspace/` e integrada em `79fd5da`, sem mesclar a branch de origem:

- antes de mover ou remover área existente, conferir `git worktree list --porcelain` e se há sessão ou agente ativo;
- realocar com `git worktree move`, remover com `git worktree remove`;
- nunca `rm -rf` em worktree registrada — branch e commits vivem no `.git` do repositório principal, e apagar o diretório manualmente deixa o registro órfão;
- mover ou remover área existente exige autorização do titular;
- realocar para `.workspace/` não altera branch, HEAD, índice nem conteúdo: conferir os quatro antes e depois, e remover a origem só após validar o destino.

## Consolidação do workspace

Em 11/11, as pastas auxiliares externas `C:/Marketing-Docs`, `C:/Marketing-Integration` e `C:/Marketing-Reviews` foram auditadas. Os dois clones independentes que continham foram realocados para `.workspace/clones/` com integridade conferida antes e depois: HEAD, tree do HEAD, branch, refs locais e remotas com objectnames, contagem de arquivos, soma de bytes e SHA-256 de `.git/config` idênticos. As três raízes externas foram removidas por estarem vazias, com `rmdir` não forçado. Nenhuma branch, commit, arquivo não rastreado ou evidência foi perdido.

## Auditoria das branches não integradas

Consulta em 11/11 sobre as 15 branches remotas então não contidas na main, sem mesclar nada. Método: `git cherry` (equivalência de patch-id), `git merge-tree --write-tree` (dry-run do efeito líquido e dos conflitos), comparação de conjuntos com `git ls-tree` e comparação de conteúdo por arquivo-chave.

| Classificação | Qtd | Observação |
| --- | --- | --- |
| Superseded — conteúdo já na main | 13 | quatro com merge neutro (tree idêntico ao da main); as demais conflitam só porque a main tem versões mais novas |
| Obsoleta e em contradição com a regra | 1 | `registra-areas-de-trabalho-isoladas`, propunha `.worktrees/` e alterar o `.gitignore` versionado |
| Trabalho real pendente | 1 | `ai-memory-integration`, PR #1 |

Fatos determinantes: `catalogo-formatos-sociais` é o R001 original, superseded pela reconciliação `8e17785`; `core-beat-plan-v1` é o BeatPlan original, superseded por `7d919fc`, e mesclá-lo **regrediria** a CLI (145→100 linhas), os testes (1187→1050) e removeria dois testes que só existem na main; `historico-apresentacoes-salao02` traz o briefing NS-001 com 237 linhas contra 327 na main (versão 0.3).

Ressalvas de método registradas: `git cat-file -e origin/main:<caminho iniciado por ponto>` falha por conversão de caminho do MSYS no Git Bash, gerando falsos "ausente" — resultados de ausência devem ser reconferidos por comparação de conjuntos com `git ls-tree`; e validação de links precisa incluir diretórios (`git ls-tree -r -d`), pois links com barra final não aparecem na listagem só de arquivos.

## Limpeza de branches — registro de recuperação

Por autorização explícita do titular, 14 branches remotas foram excluídas em 11/11: as 13 superseded e a obsoleta. Pré-condições verificadas: classificação reconferida contra a main; única PR aberta era a #1, fora do conjunto; nenhuma das 14 existia localmente nem estava checked out; checkout limpo, sem travas.

**Esta tabela é o registro de recuperação.** As refs locais de arquivo (`refs/archive/limpeza-2026-11-11/*`) existem apenas na estação onde a limpeza foi executada e não viajam pelo Git. Para restaurar qualquer uma, use o SHA abaixo:

| Branch excluída | SHA |
| --- | --- |
| `codex/alinha-regra-notificacoes-marketing` | `08a39698af55b1821837dce3dcdc5751a235e8f3` |
| `codex/core-composition-v1` | `1515b06e4a785d814b0a0116d942b09f19135065` |
| `codex/core-project-manifest` | `eda7c8e2c1a09ee1e008c8d8d233547a86489423` |
| `codex/documenta-pipeline-criativo-modular` | `a4f5de428a3a06951c69294607bebae6d782cf2c` |
| `codex/documenta-plataforma-modular-marketing` | `c6933d8c1e0d06b842e87d4ee4457356bf088ce4` |
| `codex/ns-001-consolida-validacao-executada` | `10cca3e1f2dc09b66d6568c59b87705a059d1ef5` |
| `codex/ns-001-hooks` | `c58c6e9f878c84c039cc317ac0846e6a866a2da4` |
| `codex/ns-001-roteiro-001` | `3df83f314447e823ef89525c92a5c2005c8d9b8d` |
| `codex/ns-001-validacao-agenda` | `2772da7ab1616ba4235e356b83df921e15578a8b` |
| `codex/temporal-01-piloto-orquestracao` | `a5a96f475fc34e410857952c6f7c3e0e4646ce59` |
| `codex/catalogo-formatos-sociais` | `061c2e5b5de980a1b7ff3b6da3d0e3f009aa3cf9` |
| `codex/core-beat-plan-v1` | `bade62e3a720a853e6f3d18b52aa46bf544979a4` |
| `codex/historico-apresentacoes-salao02` | `22a31ab7da56e8c35d9a27404e431a18680d75e6` |
| `codex/registra-areas-de-trabalho-isoladas` | `636e5c434c6bc0c990b4451946c56853b309a8b1` |

Restauração, se o commit ainda estiver retido pelo remoto ou existir em algum clone:

```bash
git push origin <SHA>:refs/heads/codex/<nome-da-branch>
```

A exclusão foi conferida por `git ls-remote --heads origin`: 21 branches antes, 7 depois, com verificação individual de ausência de cada uma das 14. A `main` não foi alterada pela exclusão. As cinco branches documentais já integradas e a PR #1 foram preservadas.

Estado remoto após a limpeza: `main`; `codex/ai-memory-integration` (PR #1, única pendência real); e as cinco documentais integradas `atualiza-contexto-beat-plan-v1`, `atualiza-contexto-regra-armazenamento`, `reconcilia-beat-plan-v1`, `regra-armazenamento-workspace`, `seguranca-worktrees-workspace`.

## Correção de recorte histórico

O contexto recebido de outra estação tinha inconsistência interna: a subseção "Limites atuais" da fatia Workflow afirmava que o gate Elephant–Goldfish de TEMPORAL-02 estava pendente, enquanto a seção da execução local afirmava que fora executado. Apurado na fonte: `orchestration/temporal/docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md` cobre 16 pontos com veredito OK, registra "nenhum bloqueador remanescente" e conclui "Gate aprovado para a execução local". A subseção era um recorte histórico de `f584210` com título de estado corrente; foi renomeada e rotulada como histórico, apontando para o estado corrente, com os oito bullets originais preservados. Correção na branch `codex/corrige-contexto-raiz-portavel`, ainda não integrada.

## Decisões do titular registradas

- Ratificação da fatia Workflow de TEMPORAL-02 em escopo estrito de `f584210`, sem aprovar o PRD completo nem autorizar fatia posterior.
- Regra permanente de armazenamento na raiz do projeto, com `.workspace/` por categoria e tarefa.
- Preservar os originais externos do aplicativo e de outro processo, com cópias internas verificadas, em vez de apagá-los.
- Manter `C:/Marketing` como raiz nesta estação, sem realocar para `C:/Repos`.
- Corrigir a inconsistência do contexto em branch separada, e alinhar com a outra estação antes de integrar.
- Excluir as 13 branches superseded e a obsoleta `.worktrees`.
- Versionar o histórico da sessão para que viaje entre estações.

## O que permanece local e não viaja

Ficam em `.workspace/`, ignorado pelo Git, apenas na estação onde foram produzidos: logs operacionais de cada tarefa, manifesto de migração do workspace, baselines e pós-movimento dos clones, saídas de `merge-tree` da auditoria, diffs de revisão, cópias dos briefs e da saída de ferramenta do aplicativo, e o dump de rebase de outro processo. Este documento resume os fatos duráveis desses registros; não é um backup deles.

Exceção conhecida e não resolvida: o aplicativo grava anexos do usuário e saídas grandes de ferramenta em diretório temporário próprio, fora da raiz, e outro processo deixou um dump de segurança de rebase em `/tmp`. Cópias foram preservadas dentro de `.workspace/archives/` com SHA-256 conferido; os originais externos foram mantidos por decisão do titular. Eliminar essa exceção na origem exige configuração do aplicativo.

## Pendências

- Integrar `codex/corrige-contexto-raiz-portavel` (`1d731cf`, `83eb4e5`) na main, depois do alinhamento com a outra estação, para que a regra portável valha em todas.
- Decidir o arquivamento das cinco branches documentais já integradas.
- Decidir o destino da PR #1 (`ai-memory-integration`): 19 arquivos ausentes da main, incluindo `tools/memory_sync.py`, testes, seeds de memória e um workflow de CI novo; conflita em `.ai-memory.toml`, `.gitignore` e `AGENTS.md`. Exige reconciliação com o `AGENTS.md` atual e autorização específica do CI.
- Produção, servidor Temporal remoto, namespace de produção, `contentHash`, combinação de OutputPlan ou BeatPlan com Temporal, TEMPORAL-04, mídia, fornecedores e deploy continuam bloqueados.