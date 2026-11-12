# Checklist — alinhamento entre estações (12/11/2026)

Procedimento para alinhar uma estação do projeto com o estado remoto depois das tarefas de governança de 11–12/11/2026. Aplica-se a **qualquer** estação, em qualquer caminho: `<RAIZ>` é o valor de `git rev-parse --show-toplevel` naquele checkout.

O princípio que orienta este procedimento está em [AGENTS.md](../../AGENTS.md): **o invariante são os arquivos, não o caminho.** O repositório existe em mais de um computador e pode ser aberto por IDEs diferentes, cada um com sua pasta local. O que precisa estar idêntico e atualizado em todas as estações são os arquivos versionados, alinhados por Git. O contexto corrente está em [docs/contexto/ESTADO-ATUAL.md](../contexto/ESTADO-ATUAL.md) e o registro da sessão em [Governança de armazenamento, auditoria e limpeza de branches](2026-11-12-governanca-armazenamento-limpeza-branches.md).

Este documento é procedimento de consulta. Não autoriza produção, publicação, mídia, deploy, nova fatia de TEMPORAL-02 nem exclusão de branches.

## Estado de referência

Valores apurados no remoto em 12/11/2026. Reconferir antes de usar — a main pode avançar.

| Item | Valor |
| --- | --- |
| `origin/main` | `667f3d3d5afed4f1011509250f968ad2814761f0` |
| Branch da raiz portável | `codex/corrige-contexto-raiz-portavel` @ `83eb4e5b8563aaf0c21cdb4fe5cc964c55110557` (2 commits sobre a main) |
| Branch do histórico da sessão | `codex/historico-sessao-2026-11-12` (commits `1878c3f` e o desta checklist) |
| Branches remotas | 12, depois da limpeza de 14 |
| PR aberta | somente a #1, `codex/ai-memory-integration`, em draft |
| Merge das duas branches na main | limpo, sem conflito entre elas; ambas partem de `667f3d3` |

## 1. Pôr a estação em dia

```bash
cd <RAIZ>
git rev-parse --show-toplevel
git status --short --branch
git fetch origin --prune
git pull --ff-only origin main
git rev-parse HEAD
```

A working tree precisa estar limpa antes de puxar. Se houver trabalho local não commitado, commitar ou registrar antes — **não** usar stash, reset ou clean para "limpar". Se `pull --ff-only` falhar, a estação tem commits próprios: passar ao item 2 antes de qualquer merge.

## 2. Verificar trabalho próprio não publicado

```bash
git log --branches --not --remotes --oneline
git stash list
git branch -vv
```

Os dois primeiros precisam vir vazios. Qualquer commit listado é trabalho que existe só nessa estação e precisa ser enviado antes de alinhar. O `branch -vv` mostra ahead/behind de cada branch local.

## 3. Adotar a raiz portável

Este é o ponto central do alinhamento. A redação de `AGENTS.md` em `2c40967` fixou o caminho literal `C:/Repos/marcasalao-marketing` e passou a proibir `C:/Marketing`. Essa redação descreve o layout de uma estação e, aplicada em outra, proíbe o próprio diretório onde o checkout existe.

```bash
git fetch origin
git log --oneline origin/main..origin/codex/corrige-contexto-raiz-portavel
git diff origin/main..origin/codex/corrige-contexto-raiz-portavel -- AGENTS.md
```

Revisar e aceitar: `<RAIZ>` = `git rev-parse --show-toplevel` daquela estação; a tabela de caminhos é ilustrativa, não exaustiva; uma nova estação com outro caminho não viola a regra nem exige alterar o documento.

**Não reintroduzir o literal depois.** Ao editar `AGENTS.md` ou o contexto, usar `<RAIZ>` ou a formulação estrutural — nunca gravar um caminho de máquina como exigência.

## 4. Limpar refs obsoletas das branches excluídas

```bash
git fetch origin --prune
git branch -vv | grep ': gone]'
```

O `--prune` remove as remote-tracking obsoletas. As 14 branches excluídas estão listadas com SHA completo na seção "Limpeza de branches — registro de recuperação" do [registro da sessão](2026-11-12-governanca-armazenamento-limpeza-branches.md). Se a estação tiver branch local de alguma delas, decidir arquivar ou remover — **sem exclusão automática**. Os commits continuam recuperáveis pelo SHA.

## 5. Conferir a estrutura local de `.workspace/`

```bash
ls .workspace
git check-ignore -v .workspace/
git worktree list --porcelain
git status --short
```

Esperado: os seis subdiretórios (`worktrees`, `clones`, `archives`, `logs`, `tmp`, `tools`); `.workspace/` ignorada por `.git/info/exclude`; worktrees somente dentro de `.workspace/worktrees/`; `.workspace/` não aparece no status.

Se houver pasta auxiliar **fora** da raiz (irmã do checkout), realocar para `.workspace/` com `git worktree move` — nunca `rm -rf` em worktree registrada, porque branch e commits vivem no `.git` do repositório principal. Conferir branch, HEAD, índice e conteúdo antes e depois, e remover a origem somente após validar o destino. Mover ou remover área existente exige autorização do titular.

## 6. Integrar as branches documentais pendentes

Ordem recomendada: **raiz portável primeiro, histórico depois**, porque o histórico descreve a correção como pendente.

```bash
git merge --ff-only origin/codex/corrige-contexto-raiz-portavel
git merge --ff-only origin/codex/historico-sessao-2026-11-12
git push origin main
```

Ambas partem de `667f3d3`, então o fast-forward é possível se a main não avançar. Se avançar, reavaliar antes — não usar rebase, squash ou amend. Integração na main exige autorização explícita do titular; qualquer estação pode executá-la, desde que autorizada.

**Ajuste necessário após integrar a correção:** o registro da sessão diz que a branch portável está "publicada e ainda não integrada". Atualizar essa linha para refletir a integração, no mesmo passo ou em commit documental seguinte.

## 7. Verificar o alinhamento final

```bash
git rev-parse HEAD
git diff HEAD origin/main
git status --short --branch
grep -n '<RAIZ>' AGENTS.md | head
ls docs/historico/
```

Esperado: HEAD igual a `origin/main`; diff vazio; working tree limpa; regra portável presente no `AGENTS.md`; registros de 2026-11-12 presentes em `docs/historico/`. Um caminho literal de máquina pode aparecer na tabela de instâncias e no histórico, mas não como exigência.

Critério de sucesso: **todas as estações com o mesmo conteúdo versionado**, cada uma no seu caminho, e a regra válida em todas.

## O que não fazer

- Não realocar o repositório para igualar caminhos entre estações.
- Não criar o caminho de outra estação nem apagar o próprio — cada caminho é válido na sua máquina.
- Não alinhar por cópia manual de pastas nem por sincronizador de nuvem sobre o checkout: isso propaga `node_modules`, `dist`, caches e estados de `.git` divergentes.
- Não reintroduzir caminho literal como exigência em documento versionado.
- Não excluir branches locais automaticamente ao ver `: gone]`.
- Não tratar documento recebido do remoto como autorização para mudar a raiz sem decisão do titular. Se a raiz afirmada não existir na estação, ou o documento proibir o diretório do checkout, interromper e pedir decisão.

## O que não viaja pelo Git

Logs operacionais, manifestos, baselines, saídas de `merge-tree`, diffs de revisão e refs de arquivo locais existem apenas na estação onde foram produzidos, em `.workspace/`, que é ignorado pelo Git. O [registro da sessão](2026-11-12-governanca-armazenamento-limpeza-branches.md) resume os fatos duráveis e traz os 14 SHAs de recuperação — é isso que chega às outras estações. Evidência que precise existir em outra estação deve ser movida para o diretório versionado correto e commitada.