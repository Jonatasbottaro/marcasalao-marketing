# RELATÓRIO MASTER — MIGRAÇÃO HYPERFRAMES HF-001

Operação Master HF-001 (27/11/2026): promoção do **HyperFrames 0.9.103** a motor
principal de composição/renderização audiovisual do projeto Marca Salão Marketing,
preservando o sistema existente (fábrica Python/FFmpeg, contratos TS, governança
multi-tenant, filas, aprovações, entregas) como orquestração + inteligência
editorial + governança.

> **Nota metodológica sobre as seções A–AD:** o anexo original do briefing foi
> excluído do diretório temporário do aplicativo antes do fechamento e os títulos
> exatos das seções não foram recuperáveis dos registros da sessão. Este relatório
> reconstrói as 30 seções (A–AD) em torno das dimensões naturais da operação,
> mantendo o contrato do briefing: **status por fase (Concluída/Parcial/
> Bloqueada/Não iniciada) com evidência verificável**. Nenhuma seção foi omitida;
> a numeração A–AD está completa.

Evidência por fase: [EVIDENCIAS.md](EVIDENCIAS.md). Critérios:
[CRITERIOS-DE-ACEITE.md](CRITERIOS-DE-ACEITE.md). Estado das fases:
[PLANO-DE-EXECUCAO.md](PLANO-DE-EXECUCAO.md).

---

## A — Objetivo e escopo da operação

**Status: Concluída.**

Substituir o caminho de composição/renderização audiovisual pelo HyperFrames
(HTML declarativo + runtime seekable + Chrome headless pinado) mantendo: a fábrica
legada congelada (`preset_runner`/`factory_cli`), o render local FFmpeg como
fallback operacional explícito, os contratos TS (`platform/`) **intocados**, os
templates históricos de terceiros **não editados**, a governança multi-tenant
(guardrails por marca) e o padrão VIDEO CLEAN (MKT-VIDEO-002). Decisão canônica:
[MKT-VIDEO-003](../decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md).

Escopo executado: 18 fases F0–F18, de auditoria Git à entrega de PRs em rascunho,
na branch técnica `codex/hyperframes-core-migration` — **sem merge para `main`**.

## B — Base técnica e estado inicial (F0)

**Status: Concluída.**

- Base escolhida: `codex/operacao-resultado-26` @ `3cf2fdc` (= `main` `7f1c7ff` +
  6 commits, incluindo `tenants/marca-salao/frame.md` e o fix VIDEO CLEAN do
  Studio `56f6800`); merge-base com `main` = ponta da `main` (base fast-forward
  limpa).
- Commits não enviados da operação anterior enviados ao remoto (preservação entre
  estações, regra AGENTS.md).
- PRs pré-existentes #33/#34/#35 confirmados via API pública do GitHub; nenhum
  tocado.
- Worktree da tarefa criada em `<RAIZ>/.workspace/worktrees/hf001` conforme
  AGENTS.md; nenhuma worktree pré-existente removida.

## C — Autorizações observadas e restrições respeitadas

**Status: Concluída.**

Autorizado e executado: auditoria, documentação, instalação local, componentes,
adaptadores, testes, materiais de revisão fictícios, commits seletivos em branch
técnica, pushes normais da branch técnica, PRs em rascunho.

Respeitado integralmente (nada violado): **sem** merge para `main`, deploy,
publicação/agendamento, serviços pagos, render em nuvem, `hyperframes publish`,
login HeyGen, compartilhamento público, exclusão de trabalho anterior, mudança
permanente de máquina, remoção de worktrees pré-existentes, exposição de
credenciais. `autoPublish: false` em toda a operação; `platform/src` sem
alteração; templates históricos intactos; VIDEO CLEAN em toda produção nova.

## D — Auditoria documental e inventários (F1)

**Status: Concluída.**

Leitura direta dos arquivos (decisões, governança, arquitetura, tenants,
templates, campanhas) registrada em
[INVENTARIO-DOCUMENTAL.md](INVENTARIO-DOCUMENTAL.md) e
[INVENTARIO-FUNCIONAL.md](INVENTARIO-FUNCIONAL.md).

## E — Matriz de migração e decisão MKT-VIDEO-003 (F2)

**Status: Concluída.**

- [MATRIZ-DE-MIGRACAO.md](MATRIZ-DE-MIGRACAO.md): 20 recursos com decisão
  (MANTER/ADAPTAR/MIGRAR/FALLBACK/LEGADO), compatibilidade, testes e risco.
- [MKT-VIDEO-003](../decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md)
  redigida; contradições históricas com MKT-VIDEO-001/MKT-PIPELINE-001 resolvidas
  por **notas datadas**, preservando os registros originais.

## F — Instalação do runtime HyperFrames 0.9.103 (F3)

**Status: Concluída. Commit `89ef85f`.**

- `renderers/hyperframes/package.json`: `hyperframes` **0.9.103 exato** +
  `@hyperframes/producer` 0.9.103; `engines.node >= 22` (estação: v24.22.1).
- `doctor` ok após env (FFmpeg portável no PATH) + `browser ensure`
  (Chrome pinado `chrome-headless-shell` `win64-158.0.8127.88`, ~717 MB, cache
  confinado).
- Smoke end-to-end: `init → check → render draft → ffprobe` → **h264, 1080×1920,
  ~10,0 s, 0 streams de áudio** (VIDEO CLEAN), ~22,7 s de render draft.
- Telemetry desabilitada; `HYPERFRAMES_SKIP_SKILLS=1` no env (skills vendadas).

## G — Incidente de portabilidade e correção

**Status: Concluída (incidente corrigido na sessão).**

A primeira instalação gravou caches npm (106 MB) + Chrome (717 MB) em `/.workspace`
**fora de `<RAIZ>`** (caminho Windows não coberto pelo `env.sh` original).
Correção: caches movidos para `<RAIZ>/.workspace/tmp/hf001/`, diretório externo
removido, `env.sh` ganhou o case `[A-Za-z]:[/\\]*` + verificação de sanidade
(`AGENTS.md` presente na raiz resolvida). Vazamento pós-correção verificado e
eliminado (nenhum `~/.hyperframes`, `~/.cache/hyperframes`, `~/.cache/puppeteer`
ou `/.workspace` remanescente). Detalhe em [EVIDENCIAS.md](EVIDENCIAS.md).

## H — Skills HyperFrames (F4)

**Status: Concluída. Commit `5d4465c`.**

Procedimento oficial `npx skills add heygen-com/hyperframes --all`: 194 arquivos
atualizados, 25 skills em `.agents/skills/`; `skills-lock.json` **v2** com
upstream commit `cfaefdc` + hash por skill. Fazendas de symlink com caminhos
absolutos (`.claude/`, `agent/`) excluídas localmente — não commitadas.

## I — Identidade visual, frame.md e VIDEO CLEAN (F5)

**Status: Concluída (via F6).**

`adapter/tenant.mjs` parseia o frontmatter normativo do `frame.md` (cores,
tipografia, `headerOverlay`, política de áudio) — a identidade visual é consumida
por máquina, não duplicada. VIDEO CLEAN aplicado em toda produção nova: **0
streams de áudio**, sem legendas queimadas, SRT somente sob pedido, narração TXT
separada em `04-legendas/`.

## J — Adaptador contratos → composição → render (F6)

**Status: Concluída. Commit `d2442bc`.**

`renderers/hyperframes/adapter/` (`tenant.mjs`, `compose.mjs`, `hf_adapter.mjs`)
+ `scripts/hf-adapter.sh` + entrada Python `tools/render_hyperframes.py`.
Aceita `CreativeExecutionPackage` real → materializa composição → `check` →
`render` (draft/looks/delivery) → verificação `ffprobe`. Decisão registrada:
**CLI pinado** (spawn de `hyperframes/bin/hyperframes.mjs`, isolamento de
processo); `@hyperframes/producer` avaliado e mantido como opção de progresso
fino para a fila. Caminhos de entrada validados contra escape de `<RAIZ>`
(`ASSET_PATH_ESCAPE`, `PATH_ESCAPE`; `workdir`/`out` confinados). Sem fallback
silencioso para FFmpeg (MKT-VIDEO-003): falha do adaptador = veredito `ok:false`.

## K — Guardrails e VIDEO CLEAN no adaptador

**Status: Concluída.**

Caso negativo real: caption "Agenda sempre cheia, 24h sem faltas" **aborta antes
do render** com erro estruturado `GUARDRAILS_VIOLATION` (termos "24h" +
"agenda sempre cheia", matching accent-insensitive contra
`tenants/<id>/guardrails.json`). Todos os renders verificados com 0 streams de
áudio; ZIP de entrega sem `.srt` (`primary-output.mp4` + `narration.txt`).

## L — Integração Video Studio (F7)

**Status: Concluída. Commit `8ceb8d5`.**

Seleção **explícita** de motor por trabalho (`renderer.adapter`), rotas aditivas
(`/api/works/renderer/save`, `/api/hyperframes/readiness`,
`/api/works/hyperframes/preview`), preflight (ffmpeg/ffprobe + runtime HF),
entrega em `deliveries/hyperframes/<perfil>/` com o mesmo contrato
`delivery-manifest.json` (`captionsMode: clean`), revisão/empacotamento
reutilizados (peça `hyperframes:<perfil>`, decisão
`approved_for_local_delivery`). Correção latente junto: `_verify_attempt_promotion`
e `_inspect_video_or_motion_piece` respeitam `captionsMode` (vídeo clean legado
também beneficia). Trabalhos antigos sem `renderer` seguem no caminho FFmpeg —
nada muda para eles.

## M — Fila de produção e recuperação (F8)

**Status: Concluída (ressalva registrada). Commit `8ceb8d5`.**

Modalidade `hyperframes` aditiva na fila SQLite existente (mesmos estados
`queued/running/completed/failed/cancelled/interrupted`, mesmo `recover_on_startup`);
snapshot congela `tenantId` (guardrails por marca) e `renderer`; falha do
adaptador → item `failed` com `GUARDRAILS_VIOLATION`/`ADAPTER_*` — **nunca**
reprocessa em FFmpeg. Prova HTTP `tools/ci_hyperframes_queue_proof.py --port 8813`
verde: positivo (ffprobe 1080×1920@30, 14,0 s, 0 áudio; ZIP sem `.srt`), negativo
(guardrails), recuperação (`running` forjado → `interrupted` → retry →
`completed`). Regressão da fila legada `ci_studio_queue_proof.py` verde (5/5
completed). **Ressalva:** o executor é serial por workspace por construção, mas a
prova explícita de limite de concorrência sob submissão concorrente não foi
executada (critérito pendente em
[CRITERIOS-DE-ACEITE.md](CRITERIOS-DE-ACEITE.md)).

## N — Templates nativos por função narrativa (F9)

**Status: Concluída. Commit `f06c355`.**

Biblioteca de templates no compositor selecionada pelo campo neutro do contrato
`profile.beatPlan.beats[].narrativeFunction` (o `kind` legado existia só na
fábrica congelada; `platform/src` intocado): `hook` → card de marca centrado;
`demonstration` → captura como estrela com texto na base sobre scrim de
legibilidade quase sólido (WCAG AA auditado pelo gate `check`); `cta` → convite
centrado **sem aparência de botão** (frame.md). Layout genérico por geometria
(1:1/4:5/9:16/16:9; `data-resolution: square` corrigido no 1:1). Provas: reel
9:16 `instagram-reels-video` (h264 1080×1920, 14,0 s, 0 áudio) e horizontal 16:9
`youtube-video-horizontal` (h264 1920×1080, 14,0 s, 0 áudio).

## O — Stills de post/card/carrossel (F10)

**Status: Concluída. Commit `f06c355`.**

Post e card são **captura de quadro PNG** via `hyperframes snapshot` oficial
(`hf_adapter.mjs --still`), sobre o mesmo `CarouselRequest v1` do carrossel
legado (ponte de catálogo + allowlist + geometria). Ferramenta
`tools/render_hyperframes_still.py` com entrega transacional
(`01-<id>.png`… + `stills.zip` + `still-manifest.json` + `index.json`, promoção
sob lock). Função narrativa decidida pela presença de captura (com mídia →
`demonstration`; sem mídia → card de marca `hook`/`cta`). Provas: 4:5
`instagram-feed-image-portrait` → 3 PNGs **1080×1350 codec png**; 1:1
`instagram-feed-image-square` → 3 PNGs **1080×1080 codec png** (ffprobe
conferido). Negativo: claim proibida aborta **antes da captura**, sem entrega
parcial. Fallback legado `produce_carousel.py` intacto; arte estática de feed
por IA segue ComfyUI08 + guard de proveniência.

## P — Preservação da geração de imagens IA (F11)

**Status: Concluída (sem ação).**

ComfyUI08 e o guard de proveniência (`marcasalao_media_guard.py`) intocados
(matriz #13) — nenhuma substituição do fluxo oficial de arte de feed.

## Q — Campanha piloto HF-PILOTO-001-MARCA-SALAO (F12)

**Status: Concluída. Commit `eabb13c`.**

Primeira produção completa pelo novo motor, tema organização da agenda e dos
atendimentos, em
[02-reels-shorts/hf-piloto-001-organizacao-agenda/](../../02-reels-shorts/hf-piloto-001-organizacao-agenda/README.md):
3 pedidos versionados (post 4:5, carrossel 1:1 de 4 cards, reel 9:16 de 6
cenas), 5 capturas reais autorizadas do ambiente demonstrativo Meu Salão (dados
fictícios Studio Bella; CAP-01/02/03/08/10 em `fontes/`), `direcao-de-cenas.md`
e narração pronta para gravação em
`04-legendas/hf-piloto-001-narracao-reel.txt` (idêntica ao `narration.txt` do
adaptador). Entregas verificadas: post PNG **1080×1350**; carrossel 4 PNGs
**1080×1080**; reel **h264 1080×1920, 24,0 s, 0 streams de áudio**, qualidade
delivery, 6 beats (hook + 4 demonstration + cta), gate `check` verde. Achado
real do gate: o primeiro render do post reprovou WCAG AA (contraste 2,3:1/1,92:1
— scrim linear fraco sobre captura clara); corrigido no compositor (scrim
dimensionado ao bloco de texto, fundo 0,93–0,96 + badge header 26→30 px) e
re-renderizado verde; provas F10 re-executadas verdes após a correção. Guardrails
verdes em todos os textos; CTA sem botão. **Nada publicado, agendado ou
aprovado.**

## R — Avaliação e comparação NS-001 v2 × HyperFrames (F13)

**Status: Parcial — pacote pronto; decisão estética pendente do titular.
Commits `eabb13c`/`19d8430`.**

Pacote de revisão portátil em
`<RAIZ>/.workspace/tmp/hf-piloto-001/revisao/` (não versionado): `review.html`
(aviso "MATERIAL DE REVISÃO — NÃO PUBLICADO"; post, carrossel, storyboard de 6
frames, player do reel, comparação lado a lado v2 × HF), peças renderizadas,
MP4 NS-001 v2 (47,0 s; Resultado 08, PR #33 — **corrigido em HF-002: não é Op24**)
× MP4 HF (24,0 s), re-render cronometrado (**40,7 s wall,
byte-idêntico** — SHA-256 `572d1390…dcc74` nos dois) e três relatórios
(técnico/editorial/comparativo). Comparação medida por ffprobe nos eixos do
brief: qualidade visual (paridade de encode; HF agrega gate WCAG AA que pegou
defeito real; julgamento estético **deferido à revisão humana**), animação
(filtros FFmpeg por campanha vs GSAP declarativo seekable por elemento),
preparação (código por campanha vs JSON declarativo), render (HF 40,7 s medido;
**v2 não medido — declarado, não estimado**), recursos (HF mais pesado: Chrome no
pipeline), reprodutibilidade (HF byte-idêntico provado; v2 nunca testado).
**Nenhuma aprovação estética declarada** — o agente não visualiza as mídias;
tipografia, qualidade de imagem, movimento, composição, legibilidade mobile,
contraste percebido, áreas seguras, fidelidade, identidade e coerência seguem
pendentes da revisão humana.

## S — Testes, determinismo e regressão (F14)

**Status: Concluída (ressalvas registradas). Commit `51679c6`.**

Suítes do motor verdes com saída real: `smoke.sh` **PASS** (h264 1080×1920,
10,0 s, 0 áudio); `adapter-smoke.sh` **PASS** (compose → check → render draft
14,0 s 0 áudio + guardrails negativo aborta antes do render); **novo teste
dedicado de determinismo** `determinism.sh` **PASS** — dois renders draft
independentes byte-idênticos (SHA-256
`2b4778e6dbc6ae7f0be6f6ed83893665d65aacf1a1cc629c30a06b0388207ff6`) + frames-chave
2,0/7,0/13,0 s com hashes idênticos (`0484b8f9…`, `1b52cae4…`, `5dfd8698…`),
fechando a pendência do critério F6; em delivery, o reel do piloto também
re-renderizou byte-idêntico. Provas de fila verde re-executadas após o F12
(positivo/guardrails/recuperação; ZIP sha `dc30404b…e7176da`). Suítes legadas:
`run_tests.py --smoke` **415/416** e `npm test` platform **1009/1017** — as duas
únicas falhas **pré-existentes**, provadas por `git diff` vazio contra a base
`3cf2fdc` (detalhe na seção U).

## T — Gate CI rascunho

**Status: Concluída (como rascunho). Commit `51679c6`.**

`.github/workflows/hyperframes-validation.yml`: dispara **somente por
`workflow_dispatch`** — não roda em push/PR e nenhum workflow ativo foi alterado.
Matriz ubuntu+windows; runtime pinado 0.9.103; build da ponte `platform/dist`;
os três smokes; prova de stills com os pedidos versionados do piloto (PNG
1080×1350/1080×1080 codec png); prova da fila (porta 8813); invariante de mídia
fora de `.workspace/`. YAML validado por parse real (js-yaml, cache npm
confinado). **Promoção do trigger a push/PR é decisão do titular na
integração.**

## U — Falhas herdadas da base e dependências

**Status: Registradas (correção fora do escopo HF-001).**

1. `run_tests.py --smoke` 415/416 — a única falha
   (`test_publish_pack.PublishPackTest.test_08_resolve_workspace_root`) é
   **ambiental e pré-existente em worktrees**: `tools/publish_pack.py` e seu
   teste estão inalterados nesta branch (`git diff 3cf2fdc HEAD` vazio); é o
   comportamento documentado de `resolve_workspace_root` via git-common-dir; o
   mesmo 415/416 foi registrado na operação v2.8.
2. `npm test` platform 1009/1017 — a falha (`output-plan-examples`: allowlist do
   projeto exemplo contém `instagram-feed-image-portrait`/
   `facebook-feed-image-portrait` além dos cinco planos versionados) foi
   **introduzida pela base** no commit `f01ed60` (Op 24, ancestral do ponto de
   ramificação — provado por `git merge-base --is-ancestor f01ed60 3cf2fdc` e
   `git diff` vazio nos arquivos): correção pertence à linha Op 24–26 (PR #35).

Ambas são **dependência para o CI verde dos PRs C/D** — não são regressões do
HF-001.

## V — Política de atualização (F15)

**Status: Concluída.**

[ATUALIZACOES-E-ROLLBACK.md](ATUALIZACOES-E-ROLLBACK.md): versões pinadas
(HyperFrames exato, Chrome pelo CLI, FFmpeg portátil), atualização deliberada em
6 passos (pin → smoke → re-render de referência com comparação de snapshots →
skills oficiais → registro → PR rascunho), nunca automática.

## W — Rollback (F16)

**Status: Concluída.**

Três caminhos independentes: **motor** (produção volta ao FFmpeg — caminho
permanece instalado e testado; itens concluídos não são re-renderizados
retroativamente), **branch** (rollback de repositório = não fazer merge; commits
preservados no remoto; reversão por revert explícito, nunca rebase/force) e
**runtime local** (remover `node_modules` + caches; Chrome pinado preservável).
Patrimônio nunca objeto de rollback: campanhas históricas, fábrica legada
congelada, templates históricos, regras de governança.

## X — Segurança e governança (F17)

**Status: Concluída (varreduras executadas em 27/11/2026).**

- **Confinamento de caminhos:** entrada Python valida `workdir`/`out` e mídias
  contra escape de `<RAIZ>` (`ASSET_PATH_ESCAPE`, `PATH_ESCAPE`) — provado no F6.
- **Varredura de segredos (executada nesta fase, saída real):** `grep` de
  padrões (api key/secret/password/bearer/AKIA/ghp_/sk-) sobre (1) o código
  novo do HF-001 (adapter, config, scripts, tests, entradas Python), (2) os
  arquivos versionados do piloto e (3) os artefatos de entrega em
  `.workspace/tmp/hf-piloto-001/` → **nenhuma correspondência** nos três
  alvos.
- **Ausência de comandos de nuvem:** varredura por `hyperframes publish|cloud|
  auth|lambda|cloudrun` e endpoints HeyGen no código novo → única correspondência
  é a declaração `$schema` (namespace do schema) em `adapter/compose.mjs`, não
  uma chamada. Nenhum comando de nuvem/login foi executado na operação.
- **Entrega sem segredos:** ZIPs verificados nas provas de fila contêm
  somente `primary-output.mp4` + `narration.txt` (sem `.srt`, sem credenciais);
  snapshot da fila congela `tenantId` (guardrails por marca).
- **Telemetria desabilitada** e skills vendadas (`HYPERFRAMES_SKIP_SKILLS=1`);
  caches confinados em `<RAIZ>/.workspace/tmp/hf001/` (pós-incidente da seção G).

## Y — Entrega: commits, PRs e bloqueio gh (F18)

**Status: Concluída com bloqueio registrado.**

Branch `codex/hyperframes-core-migration` (9 commits de fase + este fechamento),
enviada ao remoto, **sem merge**. Mapeamento PR A/B/C/D por faixa de commits:

| PR | Escopo | Commits |
| --- | --- | --- |
| A — governança e documentação | F1/F2/F15/F16 + índices | `3fca35a` |
| B — fundação | runtime + skills | `89ef85f`, `5d4465c` |
| C — integração | adaptador + Studio/fila | `d2442bc`, `8ceb8d5` |
| D — produção | templates + piloto + F13/F14 + fechamento | `f06c355`, `eabb13c`, `19d8430`, `51679c6` + fechamento |

**Bloqueio:** `gh` ausente na estação (`command not found`, exit 127) e sem
`GITHUB_TOKEN` — os PRs não puderam ser criados como objetos do GitHub. Link
manual registrado:
`https://github.com/Jonatasbottaro/marcasalao-marketing/compare/main...codex/hyperframes-core-migration?expand=1`.
PRs pré-existentes (#33/#34/#35) intocados. **Nenhum merge para `main`.**

## Z — Evidências-chave consolidadas

**Status: Registradas (saídas reais em [EVIDENCIAS.md](EVIDENCIAS.md)).**

| Artefato | Verificação | Valor |
| --- | --- | --- |
| Smoke draft | ffprobe | h264 1080×1920, 10,0 s, 0 áudio |
| Adaptador draft | ffprobe | h264 1080×1920, 14,0 s, 0 áudio |
| Determinismo draft (2 renders) | SHA-256 | `2b4778e6…07ff6` (idêntico) |
| Frames-chave 2,0/7,0/13,0 s | SHA-256 | `0484b8f9…`, `1b52cae4…`, `5dfd8698…` (idênticos) |
| Reel piloto (delivery, 2 renders) | ffprobe + SHA-256 | h264 1080×1920, 24,0 s, 0 áudio; `572d1390…dcc74` (idêntico) |
| Reel NS-001 v2 (comparação; Resultado 08, não Op24) | ffprobe + SHA-256 | h264 1080×1920, 47,0 s, 0 áudio; `63bef7c1…360b11b` |
| Post piloto | ffprobe | PNG 1080×1350 codec png |
| Carrossel piloto (4 cards) | ffprobe | PNG 1080×1080 codec png ×4 |
| Re-render delivery cronometrado | wall | 40,7 s |
| ZIPs de fila (provas) | SHA-256 | `daea8cbc…`, `36d8571d…`, `dc30404b…` (sem `.srt`) |

## AA — Status consolidado por fase (F0–F18)

| Fase | Escopo | Status |
| --- | --- | --- |
| F0 | Auditoria Git | ✅ Concluída |
| F1 | Auditoria documental + inventários | ✅ Concluída |
| F2 | Matriz de migração + MKT-VIDEO-003 | ✅ Concluída |
| F3 | Instalação do runtime | ✅ Concluída |
| F4 | Skills HyperFrames | ✅ Concluída |
| F5 | frame.md por máquina + VIDEO CLEAN | ✅ Concluída |
| F6 | Adaptador | ✅ Concluída |
| F7 | Integração Video Studio | ✅ Concluída |
| F8 | Fila e recuperação | ✅ Concluída (ressalva: prova de concorrência pendente) |
| F9 | Templates nativos | ✅ Concluída |
| F10 | Stills post/card/carrossel | ✅ Concluída |
| F11 | Preservação ComfyUI08 | ✅ Concluída (sem ação) |
| F12 | Campanha piloto | ✅ Concluída |
| F13 | Avaliação + comparação | 🔶 Parcial (decisão estética do titular pendente) |
| F14 | Testes e CI | ✅ Concluída (falhas herdadas registradas) |
| F15 | Política de atualização | ✅ Concluída |
| F16 | Rollback | ✅ Concluída |
| F17 | Segurança e governança | ✅ Concluída |
| F18 | Commits/PRs/relatório | ✅ Concluída com bloqueio gh registrado |

Nenhuma fase Bloqueada ou Não iniciada. Duas pendências permanecem e são
decisão do titular (revisão estética F13; criação formal dos PRs/merge).

## AB — Limitações declaradas

1. **Aprovação estética não declarada** em nenhuma peça (o agente não visualiza
   mídias); o gate `check` prova contraste WCAG AA e estrutura, não julgamento
   visual.
2. **Tempo de render do motor legado não medido** nesta operação (exigiria
   re-executar a fábrica congelada); número declarado, não estimado.
3. **Prova explícita de limite de concorrência** sob submissão concorrente não
   executada (executor serial por construção).
4. **PRs não criados como objetos do GitHub** (gh ausente) — mapeamento por
   commits + link manual.
5. **Títulos exatos das seções A–AD do briefing** não recuperáveis (anexo
   excluído); estrutura reconstruída (ver nota metodológica no topo).
6. **Stills 1:1/4:5** usam center-crop do quadro 9:16 da captura — enquadrado
   nos templates, conferível na revisão humana.
7. **Suítes legadas** carregam 2 falhas pré-existentes da base (seção U) —
   dependência para CI verde dos PRs C/D.

## AC — Pendências e decisões do titular

1. **Revisão humana do pacote F13** (decisão de aceite/ajuste das peças):
   `<RAIZ>/.workspace/tmp/hf-piloto-001/revisao/review.html`.
2. **Criar formalmente os PRs A/B/C/D em rascunho** (gh/token) ou autorizar
   outra via; merge para `main` somente com autorização explícita.
3. **Decidir a promoção do gate rascunho** `hyperframes-validation.yml` de
   `workflow_dispatch` para push/PR na integração.
4. **Correção das falhas herdadas** (linha Op 24–26 / PR #35 ou autorização
   própria) para o CI verde dos PRs C/D.
5. **Reconciliações pós-integração:** `skills-lock.json` v2 (branch) vs v1 não
   rastreado do checkout principal; atualizar `platform/README.md`
   ("nenhum renderizador implementado") quando o adaptador for integrado.

## AD — Handoff e confirmação de confinamento

Handoff completo entregue no retorno final da sessão conforme AGENTS.md,
incluindo: raiz usada (`<RAIZ>`), diretórios auxiliares, arquivos permanentes no
Git, arquivos somente em `.workspace/`, worktrees, ferramentas portáteis,
temporários removidos, `git status --short` e a confirmação textual de que
nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido fora
de `<RAIZ>`, com o caminho real substituído. O estado do repositório é
recuperável: `main` intocada, branch técnica enviada ao remoto, commits
preservados, rollback documentado (seção W).
