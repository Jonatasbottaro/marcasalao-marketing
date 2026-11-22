# Consolidação documental — 2026-11-22

Relatório da tarefa "Centralizar, consolidar e organizar a documentação do projeto".
**Escopo executado: somente documentação.** Nenhum código, teste, workflow, contrato,
aprovação, calendário, UTM, credencial ou configuração de runtime foi alterado; nenhum
`git add`, commit ou push foi executado; nenhum teste, render, pipeline ou provedor foi
executado ou consultado.

## 1. Base inicial e final

| Item | Valor |
| --- | --- |
| Raiz (`<RAIZ>`) | checkout principal desta estação, por `git rev-parse --show-toplevel` |
| Base inicial da tarefa | `main` @ `05ca7fa10209c648c5ea9cfb5d8a358214c8c396` (22/11/2026, ~14:43) |
| Base final | a mesma (`05ca7fa`); trabalho não commitado, preservado em worktree |
| Branch de trabalho | `docs/consolidacao-documental-2026-11-22` (criada nesta tarefa, livre local e remotamente) |
| Worktree | `<RAIZ>/.workspace/worktrees/consol-doc` — **preservada com alterações** |
| `origin/main` local | `276ee415a171f3bac11687343265a5c704dce067` — **referência local possivelmente desatualizada**; fetch/pull não autorizados |
| Divergência | base verificada 4 commits à frente de `origin/main` local (`6d9cd18`, `01074c8`, `5058a94`, `05ca7fa`) |
| Outras worktrees | `.workspace/worktrees/utm-ab-recommendations` (`533cc4c`, já integrada; intocada) |

**Concorrência observada:** durante o dia, outra sessão na mesma estação commitou a Etapa 14
(`6d9cd18` → `01074c8` → `5058a94` → `05ca7fa`) e alternou o checkout principal para `main`.
Ao início desta tarefa não havia edição de documentação pendente por outra sessão (apenas
os commits acima), portanto não foi necessário interromper por coordenação. O checkout
principal permaneceu intocado por esta tarefa; todo o trabalho vive na worktree.

**Nota de infraestrutura:** a primeira tentativa de worktree em
`.workspace/worktrees/consolidacao-documental-2026-11-22` falhou por `MAX_PATH` do Windows
(arquivo de fixture com nome longo); o Git limpou o diretório parcial e não registrou a
worktree. A tentativa final usou o rótulo curto `consol-doc` (caminho total abaixo do
limite) e reaproveitou a branch já criada. Nenhum resíduo externo foi deixado.

## 2. Arquivos criados, alterados e movidos

**Criados (5):**
- `docs/README.md` — ponto de entrada central.
- `docs/governanca/DOCUMENTACAO.md` — política de manutenção documental.
- `docs/governanca/MAPA-DOCUMENTAL.md` — inventário consolidado classificado.
- `docs/auditorias/CONSOLIDACAO-DOCUMENTAL-2026-11-22.md` — este relatório.
- `docs/auditorias/AUDITORIA-PROJETO-2026-11-22.md` — **cópia idêntica** (44.758 bytes) do
  relatório de auditoria salvo anteriormente no checkout principal, trazida para esta base
  para que a branch documental seja autocontida. A cópia original no checkout principal
  permanece; o titular decide qual versionar (conteúdo idêntico, merge trivial).

**Alterados (17):** `README.md`, `CLAUDE.md`, `WORKFLOW.md`, `contexto_projeto.md`,
`contexto_projeto_6.md`, `docs/arquitetura-fabrica.md`,
`docs/guia-operacional-titular.md`, `docs/guia-novo-nicho.md`,
`docs/contexto/{README,ESTADO-ATUAL,PROXIMOS-PASSOS,HANDOFF}.md`,
`docs/decisoes/MKT-{VIDEO,PLATFORM,PIPELINE}-001-*.md`,
`docs/planejamento/TEMPORAL-{01,02}-*.md`.

**Movidos: nenhum. Apagados: nenhum.** Diff: 17 arquivos, +401/−251 linhas; as remoções são
blocos operacionais duplicados do README raiz cujo conteúdo canônico já existe em
`tools/produce/README.md`, `docs/arquitetura-fabrica.md` e
`docs/guia-operacional-titular.md` (conferido por busca, incluindo o ponto de extensão de
adaptadores de imagem em `tools/produce/README.md:257` e a configuração Gemini em :255).

## 3. Decisões de organização

1. **Centralização por índice, não por movimentação.** Nenhum arquivo foi movido porque
   há consumidores de código dependentes de caminho (`tools/devlog_sync.py:270,337` →
   `contexto_projeto.md`; `tools/review_dashboard.py:690,709` e gates →
   `05-review-portal/README.md`; `tools/campaign_calendar.py:443,1211,1231` →
   `docs/rastreio-utm.md`; `tools/utm_report_importer.py:1449` e `tools/utm_simulator.py:521`
   → `docs/analytics-utm-playbook.md`; filtro de CI →
   `docs/planejamento/TEMPORAL-01-*.md`; `tools/verify_egm_install.py:206,217` →
   `AGENTS.md`/`CLAUDE.md`/`docs/designs/*`). Tabela completa em
   `docs/governanca/MAPA-DOCUMENTAL.md` §4.
2. **Diretórios existentes aproveitados;** apenas `docs/governanca/` e `docs/auditorias/`
   foram criados (este último já existia no checkout principal por tarefa anterior).
3. **Raiz mantida enxuta:** `README.md` virou apresentação + entrada; `AGENTS.md` intocado
   (IDEs carregam); `CLAUDE.md` e `WORKFLOW.md` encaminham às mesmas fontes, sem versões
   independentes das regras.
4. **Histórico classificado, não apagado:** banners aditivos em `contexto_projeto.md`,
   `contexto_projeto_6.md` (snapshot da base `642f570`), nas três decisões `MKT-*` e nos
   dois planejamentos TEMPORAL, cada um indicando período/base e fonte vigente.
5. **Gerados intocados:** `05-review-portal/*`, `04-legendas/calendario-editorial.*`,
   `matriz-utm-consolidada.csv`, pacotes sociais e manifests permanecem como estão.
6. **Editorial intocado:** briefings, hooks, roteiros, legendas e posts não foram
   transformados em documentação de arquitetura nem movidos.
7. **Terceiros intocados:** `.agents/` (1199 arquivos) não reorganizado.

## 4. Conteúdo consolidado e reconciliado com o código

Reconferido por leitura na base `05ca7fa` (método: tuplas/código/schemas/disco; **sem
execução**): 5 tenants e 14 campanhas (2/4/3/2/3); faixas `smoke` 25 / `fast` 29 /
`render` 22 / `all` 51 (`tools/run_tests.py:61-134`); 9 gates
(`tools/release_check.py:302-312`); 8 domínios (`tools/release_audit.py:82-91`); 7 lentes
(`tools/editorial_qa.py:76-82`); `WEEKS_DEFAULT=4` insuficiente para 14 campanhas
(`tools/campaign_calendar.py:100,924-931`); flags reais do scaffolder (`--dry-run`/`--apply`,
modo obrigatório) e `capacityStatus` como bloco de saída, não flag; domínio 8 sem bundles =
`ok` (não existe `BUNDLES_AUSENTES` no código); métricas sintéticas e `abWinRatePct` fração.

Correções aplicadas aos documentos vigentes: tabela de campanhas do README (19 → 14 real);
contagens de módulos/faixas/lentes/domínios em README, arquitetura e guia do titular;
comandos de calendário com `--weeks 7`; comportamento real do domínio 8; ressalvas do
scaffolder e do `capacityStatus` documentadas onde antes havia promessa excessiva.
**Regras não foram reescritas para legitimar defeitos:** as divergências de código
permanecem registradas como pendências (seção 6).

## 5. Histórico preservado

- Nenhuma entrada de devlog, aceite, decisão ou marco foi apagada ou reescrita
  retroativamente; banners são aditivos.
- Medições históricas (354/422 testes e 53,4 s/375,4 s da Etapa 13.1; runs de CI citados)
  permanecem com data e base originais, agora rotuladas como históricas e não reexecutadas.
- A matriz de formatos do README foi mantida com nota de proveniência (aceites de
  14/11/2026), não como medição nova.

## 6. Divergências que dependem de correção no código (não executadas)

Lista completa e priorizada em `docs/contexto/PROXIMOS-PASSOS.md` (backlog P1–P3) e em
`docs/auditorias/AUDITORIA-PROJETO-2026-11-22.md`. Resumo:
1. E2E espera 7 domínios contra 8 emitidos (`tests/e2e/test_factory_e2e.py:185,367`).
2. Scaffolder grava antes de validar, `ok:true` fixo, sem `editorial_qa`, timing 34 s vs 30 s
   (`tools/tenant_scaffolder.py:636,642,677,391-444`).
3. Teste do scaffolder em `%TEMP%` + `os.chdir("/")`; testes de portal/calendário escrevem
   na árvore versionada (`tools/tests/test_tenant_scaffolder.py:40,62,65`;
   `test_review_dashboard.py:335-340`; `test_campaign_calendar.py:180-182`).
4. `capacityStatus` mistura escopos; `current.totalSlotsEstimate` usa total simulado
   (`tools/executive_summary.py:529-546`; `tools/campaign_calendar.py:576-577,618-619`).
5. Fadiga/benchmarks globais rotulados por tenant; `impressions/clicks/ctr` = sessões;
   docstring do z e mensagem de amostra (`tools/utm_report_importer.py:855-888,1268-1273,527,613-616`).
6. `edit_link_reel.py` com faixa AAC silenciosa, `shell=True`, FFmpeg externo (:91-96,37,12).
7. Guard Postiz não regula tipos não-draft; testes do guard órfãos de gates
   (`marcas/marcasalao/comfyui/marcasalao_media_guard.py:82`).
8. Índices `tenants/*/campaigns/README.md` listam subconjunto das campanhas.
9. Constante de marca no núcleo TS e ponte de tenant policy sem consumidor
   (`platform/src/tenant-policy-contract.ts:72`).

## 7. Verificações realizadas (somente leitura)

- Varredura de links relativos: 213 documentos próprios, 660 links; **0 quebrados após a
  criação deste relatório** (a única pendência durante a escrita era o link para este
  próprio arquivo).
- Varredura de caminhos de máquina nos documentos alterados/criados: nenhuma ocorrência
  **introduzida** pela consolidação; as 22 ocorrências detectadas são linhas históricas
  pré-existentes (devlog, seções antigas do ESTADO-ATUAL, nota do TEMPORAL-01). A menção a
  `%TEMP%` em `docs/contexto/ESTADO-ATUAL.md:43` descreve o defeito do teste, não um caminho
  usado.
- Varredura de segredos nos documentos tocados: 0 ocorrências.
- `git status`/`diff` da worktree: apenas os 17 `.md` alterados + 5 criados; **nenhum**
  arquivo de código, teste, workflow, schema ou configuração tocado.
- Contenção: worktree e todos os artefatos sob `<RAIZ>` verificados por `os.path.realpath`
  (não apenas prefixo de string); nenhum symlink/junction no caminho.
- Preservação de conteúdo do README: blocos removidos conferidos contra as fontes
  canônicas existentes (seção 2).

## 8. Itens não verificados / conflitos não resolvidos

- Estado remoto ao vivo (PRs, runs de CI posteriores a `9a800d1`): não consultado.
- Comportamento real de Postiz/ComfyUI/Hermes/Gemini: não consultado; descrições por código.
- Execução de qualquer teste/gate: não realizada; "gate provavelmente vermelho" permanece
  hipótese estática até execução autorizada.
- Contagens de funções de teste não medidas por execução; apenas módulos por tupla.
- Conflito não resolvido de propósito: qual cópia do relatório de auditoria versionar
  (checkout principal vs worktree) — decisão do titular na integração.
- Conflito não resolvido de propósito: índices de campanhas por tenant e correções de
  código do backlog — exigem tarefas próprias com autorização.
- `.git/info/exclude` incompleto (`bundles/`, `snapshots/`): proposta documentada em
  `docs/guia-novo-nicho.md`, aplicação por estação fora do escopo.

## 9. Limitações de atualização do remoto

`origin/main` local (`276ee41`) pode estar desatualizado; fetch/pull exigem autorização
específica e não foram executados. A branch documental existe **apenas localmente**, sem
commit e sem push; outras estações não a verão até integração autorizada. `.workspace/`,
aprovações e mídia local não sincronizam por Git.

## 10. Encerramento

- Entrada para qualquer IDE/agente: `docs/README.md` (nesta base, fisicamente em
  `<RAIZ>/.workspace/worktrees/consol-doc/docs/README.md` até integração).
- Worktree com mudanças **preservada**; nenhuma worktree preexistente removida.
- Nenhum auxiliar criado fora de `<RAIZ>`; nenhum temporário criado (verificações feitas
  por scripts inline somente leitura, sem arquivo em disco).
- Confirmação: nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido
  fora de `<RAIZ>` (o checkout principal desta estação).
- Esta consolidação **não** autoriza implementar o backlog, produzir mídia, publicar,
  agendar, limpar `.workspace/` ou integrar branches.