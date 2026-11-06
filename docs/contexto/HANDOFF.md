# Handoff: retomar o projeto

Este arquivo descreve a retomada. Os fatos que mudam ficam em [ESTADO-ATUAL.md](ESTADO-ATUAL.md); as prioridades ficam em [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md). Não copiar suas tabelas para cá.

## 1. Recuperar a referência correta

Leia AGENTS.md e o [índice de contexto](README.md). No computador de trabalho, identifique o clone ou worktree real, a branch, o remoto e as alterações locais.

Comandos de inspeção:

```bash
git rev-parse --show-toplevel
git status --short
git remote -v
git branch --show-current
git fetch origin --prune
git log -8 --oneline
```

Uma pasta sincronizada sem .git pode conter arquivos úteis, mas não comprova a identidade do commit executado. Preserve alterações locais e use uma cópia isolada quando houver risco de mistura. Atualize por fast-forward somente quando o checkout e a branch permitirem; não descarte trabalho para sincronizar.

Em uma sessão que só tenha a integração do GitHub, leia as mesmas referências no remoto e informe esse limite. Não afirme ter verificado o computador local.

## 2. Comparar o contexto com o Git

- Confira o código da main e a situação real das PRs referenciadas no estado atual.
- Diferencie código integrado, branch de trabalho e proposta documental.
- Leia o README da platform do commit em que a tarefa será executada.
- Confira se a funcionalidade proposta já existe em alguma branch relevante.
- Quando o snapshot documental estiver antigo, corrija o estado com evidência do remoto; não use uma conversa ou anexo anterior como substituto.

## 3. Escolher uma tarefa e verificar o resultado

Defina um incremento com consumidor e critério de conclusão claros. Use os scripts realmente presentes no package.json da branch; um comando disponível numa PR pode não existir na main anterior à integração.

Para mudanças de código, use instalação pelo lockfile, verificações de tipos e testes apropriados. Para alterações apenas documentais, confira links, referências e coerência factual; não é necessário refazer serviços ou geração de mídia por causa da documentação.

Mantenha distintos:

- resultado observado em execução própria;
- resultado de CI consultado e vinculado a um HEAD;
- resultado apenas relatado em documento;
- hipótese ou ponto ainda não verificado.

## 4. Registrar a passagem

Ao encerrar:

- informe base, branch, commit/PR e arquivos alterados;
- registre verificações e limitações, incluindo ocorrências ainda sem diagnóstico;
- atualize ESTADO-ATUAL.md quando o estado técnico mudar;
- atualize a lista de prioridades somente quando a conclusão alterar a próxima tarefa;
- preserve as aprovações e os estados dos documentos editoriais.

## Limites da retomada

O handoff é contexto, não uma autorização independente. Continuam valendo o pedido atual e AGENTS.md: produção, dados, publicação, credenciais e memória têm seus próprios limites. Não importar transcrições completas, configurações privadas ou históricos de outros projetos para tentar preencher lacunas.
