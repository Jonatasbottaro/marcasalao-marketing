# Handoff: retomar o projeto

## Operação Resultado 03 — NS-001, distribuição manual e mensuração real (24/11/2026)

- **Base:** `main` @ `bcabc00`. Registros versionados em
  [`02-reels-shorts/ns-001-reels-organizacao-agenda/resultado-03/`](../../02-reels-shorts/ns-001-reels-organizacao-agenda/resultado-03/RELATORIO.md)
  e [`docs/historico/2026-11-24-operacao-resultado-03-ns001.md`](../historico/2026-11-24-operacao-resultado-03-ns001.md).
- **Gate de publicação reprovado; nada publicado/agendado.** A Resultado 02 aprovou editorialmente a
  produção e gerou vídeo real de revisão (47 s, 0 áudio) na branch `feat/ns-001-resultado02-producao`
  @ `5412db4` (worktree `.workspace/worktrees/ns001-resultado02`, **integrada na main via merge
  `7e9c41c` em 24/11/2026**, autorizado pelo titular). Publicação,
  decisão 7 (CTA/destino/bio/UTM) e revisão humana seguem pendentes.
- **Destino reprovado** no teste renderizado (desktop+celular): site exibe "Meu Salão", jornada de
  marketplace/assinatura incompatível com o CTA e claims proibidos/sem evidência. Bloqueio de
  publicação registrado; site não alterado.
- **Recomendação única:** C — ajustar CTA ou destino antes da próxima campanha. NS-002 não iniciada.
  Ciclo **pendente** até publicação manual efetiva do titular.
- **Próxima ação do titular:** decidir nome público/destino, assinar decisão 7, conferir bio IG +
  mecanismo Shorts, revisar a peça v1 e autorizar publicação manual. (Integração da branch de
  produção já realizada: merge `7e9c41c`.)

## Operação Finalização — PR #29 com CI verde (24/11/2026)

- **Branch:** `fix/release-check-portabilidade` @ **`6b81d33`** (push em `origin`); base `main` @ `423f720`. PR #29 **em rascunho**, sem merge/deploy/publicação.
- **Cadeia de correções desta rodada:**
  1. `7615c63` — `test_derivative_formats.test_09` exigia `.workspace/archives` local (ausente em checkout limpo); trocada por asserção de resolução determinística. Resolveu o step 10 do CI.
  2. `6b81d33` — fixture do E2E do Studio (`_prepare_isolated_workspace` em `tools/tests/test_campaign_studio_e2e.py`) copiava só `tools/`+`platform/`; sem `tenants/` o preflight bloqueava (`nenhum tenant disponivel para o preflight`, `video_studio.py:850`). Agora copia também `tenants/`, `schemas/`, `02-reels-shorts/`, `01-insta-stories/`, `04-legendas/` (contrato de `test_studio_work_backup._copy_repo_subdirs`). +12 linhas, só fixture; produção intacta.
- **Verificação local:** E2E Studio `REQUIRE_RENDER=1` 2 testes OK (render real, ZIP, backup/restauração); 169 testes render + 36 backup OK; step 10 combinado 416 OK; `release_check.py --json` completo **com TypeScript** → 9/9 gates ok, exit 0.
- **CI verde (SHA `6b81d33`):** runs [45387139303](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/45387139303) e [45387127507](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/45387127507) — Ubuntu e Windows `success`, 41 steps cada, render obrigatório e provas E2E incluídos.
- **Evidências locais:** `.workspace/logs/pr29-finalizacao/checkpoint-B.md` (causa raiz, reprodução, níveis 1-4) e `.workspace/tmp/repro-ci/` (logs de reprodução, lotes e release).
- **Próxima etapa:** Etapa 2 — homologação operacional/editorial da NS-001. Diagnóstico somente-leitura em `.workspace/logs/pr29-finalizacao/diagnostico-ns001-etapa2.md`: briefing v0.3 em validação, roteiro rascunho, capturas fixture, UTMs `aguardando_aprovacao_titular`, nada autorizado para gravação/publicação. **Aprovação explícita do titular necessária.**
- **Restrições respeitadas:** nada fora de `<RAIZ>`; `.workspace/` local não versionado; nenhum trabalho de outra sessão descartado; PR em rascunho.

## Etapa 1 — estabilização do release (correção final do gate 8, 23/11/2026)

- **Branch:** `fix/release-check-portabilidade` @ `de91076` (push em `origin`); base `main` @ `423f720`. Arquivos temporários em `.workspace/` (não versionados).
- **O que foi feito (commit `de91076`, posterior a `1149a03`):**
  1. Reproduzida a falha do gate 8 em condições de CI: com o FFmpeg vindo do PATH num diretório `bin/` (como no runner), `test_09_ffmpeg_ausente` falhava com `AssertionError: True is not false` — o filtro de PATH por nome de pasta só funcionava na estação (pasta portátil `ffmpeg`).
  2. `test_09_ffmpeg_ausente` agora remove do PATH apenas a entrada que expõe o ffmpeg real (`shutil.which`), preservando as demais; funciona no runner e na estação.
  3. `test_25_ffprobe_metadata_encontra_ffprobe_real` usa a descoberta efetiva (PATH ou cópia portátil) sem mock; com `REQUIRE_RENDER=1` e nenhum ffprobe, falha em vez de skipar.
  4. `test_executive_summary.test_23` gera relatórios e portal em sandbox próprio, sem apagar `.workspace/reports/<tenant>/` compartilhado.
  5. `test_release_audit` 25/26 e `test_run_tests.test_17` usam fixtures sintéticas de archives, sem depender de acervo real não versionado da estação.
- **Verificação local (Windows, PATH estilo runner, Python 3.13.15):** `release_check.py --skip-ts --json` **9/9 gates, exit 0**; `unit_tests` **456/456 passed / 0 failed / 0 errors / 0 skipped**; `workspace_doctor` ok (ffmpeg/ffprobe origem `PATH`); módulos doctor 51/51; `tenant_validator`, `factory_cli`, `utm_simulator`, `release_audit --strict` (8/8), E2E e `git diff --check` aprovados.
- **CI (desfecho em 24/11/2026):** runs `45257399186`/`45257382687` (SHA `de91076`) falharam no step 10 por `test_derivative_formats.test_09` (dependência de `.workspace/archives` local) — corrigido em `7615c63`; gate 8 passou. Desfecho completo na seção de 24/11/2026 no topo (CI verde em `6b81d33`).
- **Pendente (resolvido em 24/11/2026):** CI verde confirmado nos dois sistemas; PR #29 segue em rascunho (https://github.com/Jonatasbottaro/marcasalao-marketing/pull/29) aguardando revisão/integração do titular. Não merge, não publicar redes sociais, não deploy.
- **Restrições respeitadas:** nada fora de `<RAIZ>`; `.workspace/` local e não versionado; nenhuma branch/trabalho de outra sessão excluído.

## Etapa 1 — estabilização do release (concluída com êxito, 23/11/2026)

- **Branch:** `fix/release-check-portabilidade` @ `eb3c064` (push em `origin`); base `main` @ `423f720`. Arquivos temporários em `.workspace/` (não versionados).
- **O que foi feito:**
  1. Instalado ffmpeg/ffprobe portátil via `tools/bootstrap_ffmpeg.py` em `<RAIZ>/.workspace/tools/ffmpeg/` (ffmpeg 9.1-essentials, validado com `-version`), sem instalação global.
  2. Testada descoberta de binários reais (PATH e portátil) no `workspace_doctor.py`; teste 09 (`ffmpeg_ausente`) ajustado para isolar PATH de poluição global.
  3. Adicionados testes 25 (`_ffprobe_metadata` com ffprobe real via PATH) e 26 (retorna `None` sem ffprobe) em `tools/tests/test_workspace_doctor.py`. 26/26 testes OK isolados.
  4. `python tools/release_check.py --json` (sem `--skip-ts`): **9/9 gates aprovados**, exit code 0 (higiene_git, typescript, tenant_validator, editorial_qa, workspace_doctor, release_audit, bundling, unit_tests `--fast` com 453 passed / 0 failed / 0 errors / 3 skipped, e2e OK).
  5. Gate 8 corrigido: 5 testes condicionados à ausência de `.workspace/archives/`/`.workspace/reports/` pulam (skip) quando o estado da estação não tem esses arquivos locais não versionados; cada módulo passa isoladamente e no suíte completo.
  6. Worktree órfão não registrada em `.workspace/worktrees/fix-release-check-portabilidade/` removida.
  7. Commit `eb3c064` e push feitos na branch `fix/release-check-portabilidade`.
- **Pendente:** criar PR em rascunho contra `main` (link manual: https://github.com/Jonatasbottaro/marcasalao-marketing/compare/main...fix/release-check-portabilidade?expand=1; `gh` não instalado e sem `GITHUB_TOKEN`); consultar GitHub Actions (Ubuntu + Windows) após o PR; corrigir falhas relacionadas à alteração, se houver.
- **Restrições respeitadas:** não merge, não publicar redes sociais, não deploy, não excluir branches/trabalhos de outras sessões, nada fora de `<RAIZ>`, `.workspace/` local e não versionado.

## Última tarefa relevante — consolidação documental (22/11/2026)

- **Base utilizada:** `main` @ `05ca7fa10209c648c5ea9cfb5d8a358214c8c396`; trabalho isolado
  na worktree `<RAIZ>/.workspace/worktrees/consol-doc`, branch
  `docs/consolidacao-documental-2026-11-22`, **sem commit** (integração exige autorização
  própria). `origin/main` local = `276ee41`, possivelmente desatualizado.
- **Mudanças realizadas:** somente documentação — entrada central `docs/README.md`;
  `docs/governanca/{DOCUMENTACAO,MAPA-DOCUMENTAL}.md`; atualização de
  `docs/contexto/{README,ESTADO-ATUAL,PROXIMOS-PASSOS,HANDOFF}.md`, `README.md` raiz,
  `CLAUDE.md`, `WORKFLOW.md`, `docs/arquitetura-fabrica.md`,
  `docs/guia-operacional-titular.md`, `docs/guia-novo-nicho.md`; banners históricos em
  `contexto_projeto.md`, `contexto_projeto_6.md`, `docs/decisoes/*`,
  `docs/planejamento/TEMPORAL-{01,02}-*.md`; relatório
  `docs/auditorias/CONSOLIDACAO-DOCUMENTAL-2026-11-22.md`. Nenhum arquivo movido ou apagado.
- **Validações realmente executadas:** somente leitura — varredura de links relativos,
  conferência de contagens por tuplas/código, `git status`/`diff`, contenção de caminhos por
  realpath. **Nenhum teste, gate, render ou CLI do projeto foi executado.**
- **Alterações pendentes de outras sessões:** no checkout principal, a sessão concorrente
  commitou a Etapa 14 (`5058a94`, `05ca7fa`) e alternou a branch para `main`; ao início
  desta tarefa havia edições não commitadas em `tools/tests/test_run_tests.py` e
  `test_tenant_scaffolder.py`, depois commitadas por aquela sessão. Nada disso foi tocado
  aqui.
- **Próxima ação segura:** revisar o diff da branch documental e decidir integração
  (autorização própria); em seguida atacar P1 do backlog em
  [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md) (E2E de 8 domínios e scaffolder fail-closed),
  cada um com autorização e execução de gate identificada por SHA/data.
- **Limites:** esta consolidação não autoriza implementar backlog, produzir mídia,
  publicar/agendar, limpar `.workspace/` ou remover worktrees. A worktree com mudanças
  **foi preservada**.

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
