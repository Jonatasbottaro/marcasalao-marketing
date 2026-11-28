# Evidências — HF-001

Registro verificável por fase. Comandos executados na worktree
`.workspace/worktrees/hf001` (branch `codex/hyperframes-core-migration`), estação
Windows, 27/11/2026. `<RAIZ>` = raiz do checkout principal da estação.

## F0 — Auditoria Git

- `git log`/`git branch -a`/`git worktree list`: base escolhida
  `codex/operacao-resultado-26` (`3cf2fdc` = `main` `7f1c7ff` + 6 commits, incluindo
  `frame.md` e o fix VIDEO CLEAN do Studio `56f6800`); merge-base com `main` = ponta
  da `main` (base fast-forward limpa).
- Commits não enviados da op26 (`0b11214..3cf2fdc`) **enviados ao remoto** para
  preservar o `frame.md` entre estações (regra de alinhamento do AGENTS.md).
- PRs listados via API pública do GitHub (`gh` indisponível na estação): PRs #33/#34/#35
  rascunhos pré-existentes confirmados, nenhum tocado.
- Worktree da tarefa criada dentro de `<RAIZ>/.workspace/worktrees/hf001` conforme
  AGENTS.md; nenhuma worktree pré-existente removida.

## F3 — Instalação do runtime (commit `89ef85f`)

- `renderers/hyperframes/package.json`: `hyperframes` **0.9.103 exato** +
  `@hyperframes/producer` 0.9.103; `engines.node >= 22` (Node da estação: v24.22.1).
- `doctor`: inicial `ok:false` (FFmpeg ausente do PATH) → corrigido pelo env
  (`.workspace/tools/ffmpeg` no PATH) → `ok` após `browser ensure`.
- `browser ensure`: download do Chrome pinado `chrome-headless-shell`
  `win64-158.0.8127.88` (~717 MB) para o cache confinado.
- Smoke (`renderers/hyperframes/tests/smoke.sh`): `init` → `check` →
  `render --quality draft` → `ffprobe`:
  - codec h264, **1080×1920**, ~10,0 s, **0 streams de áudio** (VIDEO CLEAN);
  - tempo de render ~22,7 s (draft, estação local).
- Telemetry desabilitada (`hyperframes telemetry disable`); `HYPERFRAMES_SKIP_SKILLS=1`
  no env (skills vendadas, init não consulta GitHub).

### Incidente de portabilidade (corrigido na sessão)

- Sintoma: `git rev-parse --git-common-dir` devolve caminho Windows (`C:/...`) não
  coberto pelo `env.sh` original → caches npm (106 MB) e Chrome (717 MB) gravados em
  `/.workspace` **fora de `<RAIZ>`** (violação da regra de portabilidade).
- Correção: caches movidos para `<RAIZ>/.workspace/tmp/hf001/` (download do Chrome
  preservado); diretório externo removido; `env.sh` ganhou o case
  `[A-Za-z]:[/\\]*` + verificação de sanidade (`AGENTS.md` presente na raiz
  resolvida).
- Verificação de vazamento pós-correção: nenhum `~/.hyperframes`,
  `~/.cache/hyperframes`, `~/.cache/puppeteer` ou `/.workspace` remanescente.

## F4 — Skills (commit `5d4465c`)

- Procedimento oficial executado: `npx skills add heygen-com/hyperframes --all`.
- Resultado: 194 arquivos atualizados, 25 skills obsoletos removidos, 72 adicionados
  → **25 skills** em `.agents/skills/` (novos: `reverse-any-video`, `style-sampling`).
- `skills-lock.json` **v2** criado: upstream `heygen-com/hyperframes` commit
  `cfaefdc56dc93d74aeedc537123097f2ab74470b` + hash por skill.
- `.claude/` e `agent/` (fazendas de symlink com caminhos absolutos da worktree)
  excluídos localmente via `.git/info/exclude` — não commitados.

## F1/F2 — Auditoria e matriz (este PR)

- Inventários documental e funcional: leitura direta dos arquivos (decisões,
  governança, arquitetura, tenants, templates, campanhas) — ver
  [INVENTARIO-DOCUMENTAL.md](INVENTARIO-DOCUMENTAL.md),
  [INVENTARIO-FUNCIONAL.md](INVENTARIO-FUNCIONAL.md).
- Matriz: 20 recursos com decisão/compatibilidade/testes/risco — ver
  [MATRIZ-DE-MIGRACAO.md](MATRIZ-DE-MIGRACAO.md).
- Decisão MKT-VIDEO-003 redigida; notas de classificação datadas adicionadas a
  MKT-VIDEO-001 e MKT-PIPELINE-001 (originais preservados).

## F5–F18 — Evidências por fase

Cada fase registra aqui sua evidência ao concluir (critérios em
[CRITERIOS-DE-ACEITE.md](CRITERIOS-DE-ACEITE.md)). Nada é pré-marado: campos abaixo
são preenchidos somente com saída de comando real. Todas as fases têm evidência
registrada (F5 via F6; F11 sem ação — ComfyUI08 intocado, matriz #13).

| Fase | Evidência |
| --- | --- |
| F6 Adaptador | **Concluído (27/11/2026).** `renderers/hyperframes/adapter/` (`tenant.mjs`, `compose.mjs`, `hf_adapter.mjs`) + `scripts/hf-adapter.sh` + entrada Python `tools/render_hyperframes.py`. Smoke `tests/adapter-smoke.sh` verde: pedido real de exemplo → composição → `check` → render draft → `ffprobe` **h264 1080×1920, 14,0 s, 0 streams de áudio**; caso negativo: caption "Agenda sempre cheia, 24h sem faltas" aborta antes do render com `GUARDRAILS_VIOLATION` (termos "24h" + "agenda sempre cheia"). Decisão CLI × API: **CLI pinado** (spawn de `hyperframes/bin/hyperframes.mjs`); `@hyperframes/producer` avaliado (expõe `createRenderJob`/`executeRenderJob` + `ProgressCallback`) e mantido como opção para progresso fino na fila (F8). Determinismo por re-render com hash de frames: pendente de teste dedicado (F14). |
| F7/F8 Studio+fila | **Concluído (27/11/2026).** Modalidade `hyperframes` aditiva na fila SQLite existente (mesmos estados/recovery; sem fallback silencioso — MKT-VIDEO-003): seleção explícita de motor por trabalho (`renderer.adapter`, rotas `/api/works/renderer/save`, `/api/hyperframes/readiness`, `/api/works/hyperframes/preview`), opção de plano + preflight (ffmpeg/ffprobe + runtime HF), executor delegando ao `tools/render_hyperframes.py` em modo de entrega (`--output-dir/--staging/--attempt-id/--fence-file`, mesmo contrato `delivery-manifest.json` da fila com `captionsMode: clean`), snapshot congelando `tenantId` (guardrails por marca) e `renderer`, entrega em `deliveries/hyperframes/<perfil>/`, peça de revisão `hyperframes:<perfil>` e ZIP reutilizado (`primary-output.mp4` + `narration.txt`, sem SRT). Correção latente junto: `_verify_attempt_promotion` e `_inspect_video_or_motion_piece` exigiam `srt` incondicionalmente — agora respeitam `captionsMode` (vídeo clean legado também beneficia). Prova HTTP `python tools/ci_hyperframes_queue_proof.py --port 8813` verde: lote positivo `batch-8d4235ff77` (ffprobe **1080×1920 @30, 14,0 s, 0 streams de áudio**, peça `pending_review` → aprovação → ZIP sha `daea8cbc…f6e05a10` sem `.srt`); negativo `batch-2f4add154a` (caption "Agenda sempre cheia, 24h sem faltas" → item `failed` com `GUARDRAILS_VIOLATION`, sem reprocesso FFmpeg); recuperação `batch-9927ceeff3` (item `running` forjado → `recover_on_startup` → `interrupted`/`INTERRUPTED_INCONCLUSIVE` → `/api/queue/retry` → `completed`). Regressão das modalidades legadas na mesma árvore: `python tools/ci_studio_queue_proof.py --port 8803` verde — lote `batch-f6eb82af45` com **5/5 completed** (vídeo ×2, carrossel, motion, vídeo), ZIP sha `e023dacc…5a55174e5`. |
| F9/F10 Templates | **Concluído (27/11/2026).** Biblioteca de templates dentro do compositor (`adapter/compose.mjs`), selecionada pelo campo neutro do contrato `profile.beatPlan.beats[].narrativeFunction` (o `kind` legado existia só na fábrica congelada; `platform/src` intocado): `hook`→card de marca centrado, `demonstration`→captura como estrela com texto na base sobre scrim suave, `cta`→convite centrado sem aparência de botão (frame.md); layout genérico por geometria com `data-resolution: square` corrigido no 1:1. Provas com `tools/render_hyperframes.py` (pedido exemplo 3 beats hook/demonstration/cta): reel 9:16 `instagram-reels-video` → veredito ok, **h264 1080×1920, 14,0 s, 0 streams de áudio**, 3 beats; horizontal 16:9 `youtube-video-horizontal` → **h264 1920×1080, 14,0 s, 0 streams de áudio**. Stills (F10) pela captura oficial `hyperframes snapshot` (`hf_adapter.mjs --still`, exige 1 PNG + ffprobe codec `png`/geometria) com ferramenta `tools/render_hyperframes_still.py` sobre `CarouselRequest v1` (catálogo+allowlist via ponte; entrega transacional `01-<id>.png`… + `stills.zip` + `still-manifest.json` + `index.json`): 4:5 `instagram-feed-image-portrait` → 3 PNGs **1080×1350 codec png**; 1:1 `instagram-feed-image-square` → 3 PNGs **1080×1080 codec png** (ffprobe conferido em todos). Negativo still: card "Agenda sempre cheia, 24h sem faltas" → `GUARDRAILS_VIOLATION` (termos "24h" + "agenda sempre cheia") **antes da captura**, sem entrega parcial (diretório do pedido negativo não criado; entrega anterior intacta). Fallback preservado: `produce_carousel.py` e ComfyUI08 intocados. Regressão da fila com o novo compositor: `python tools/ci_hyperframes_queue_proof.py --port 8813` verde (`exit=0`) — positivo `batch-a940affe98`, guardrails `batch-88415b1d4b`, recuperação `batch-6fb3a53340`, ZIP sha `36d8571d…adfd9`. Avaliação estética humana é F13 (nada aprovado sem ver). **Refinamentos do piloto F12 (27/11/2026, mesma data):** (1) stills — função narrativa passa a ser decidida pela presença de captura (card com `mediaId` → `demonstration`; sem captura → card de marca, primeiro `hook`, demais `cta`), porque a convenção puramente posicional escondia a captura atrás do card de marca no post e nas capas com mídia; (2) scrim do `demonstration` redimensionado ao bloco de texto com fundo quase sólido (0,93–0,96) atrás do texto — o scrim linear antigo reprovava WCAG AA no gate `check` sobre captura clara de app (2,3:1 e 1,92:1, achado real do primeiro render do post); (3) badge do header 26→30 px (piso de leitura 28 px do `check`). Provas F10 re-executadas verdes após os refinamentos: 4:5 e 1:1 (3 PNGs cada, ffprobe png/geometria) e negativo `GUARDRAILS_VIOLATION` ("24h" + "agenda sempre cheia") antes da captura. |
| F12 Piloto | **Concluído (27/11/2026).** Campanha `HF-PILOTO-001-MARCA-SALAO` (tema: organização da agenda e dos atendimentos) em [02-reels-shorts/hf-piloto-001-organizacao-agenda/](../../02-reels-shorts/hf-piloto-001-organizacao-agenda/README.md): 3 pedidos versionados (`pedido-post.carousel-request.json` 4:5, `pedido-carrossel.carousel-request.json` 1:1 com 4 cards, `pedido-reel.video-request.json` 9:16 com 6 cenas), 5 capturas reais autorizadas do ambiente demonstrativo Meu Salão com dados fictícios Studio Bella versionadas em `fontes/` (CAP-01/02/03/08/10, 1080×1920, reutilizadas da peça editorial v2 da NS-001), `direcao-de-cenas.md` e narração pronta para gravação em `04-legendas/hf-piloto-001-narracao-reel.txt` (idêntica à `narracao.txt` gerada pelo adaptador). Renders reais pelo novo motor, todos verificados: **post** `tools/render_hyperframes_still.py` → PNG **1080×1350 codec png** (ffprobe); **carrossel** → 4 PNGs **1080×1080 codec png** (ffprobe; cards 1–3 demonstration com captura, card 4 cta de marca); **reel** `tools/render_hyperframes.py --profile instagram-reels-video --quality delivery` → **h264 1080×1920, 24,0 s, 0 streams de áudio**, 6 beats (hook + 4 demonstration + cta), gate `check` verde. Primeiro render do post reprovou o gate com `contrast_aa_failure` (2,3:1/1,92:1 — scrim linear fraco sobre captura clara): corrigido no compositor (scrim dimensionado ao bloco de texto com fundo quase sólido 0,93–0,96 + badge header 26→30 px) e re-renderizado verde; provas F10 re-executadas verdes após a correção (ver linha F9/F10). Guardrails verdes em todos os textos (nenhuma claim proibida; CTA sem botão). Regressão da fila re-executada com o compositor final: `python tools/ci_hyperframes_queue_proof.py --port 8813` verde (`exit=0`) — positivo `batch-ad6f52a5e2`, guardrails `batch-7083a33f0b`, recuperação `batch-1080598bbc`, ZIP sha `dc30404b…e7176da`. Renders e pacote de revisão em `<RAIZ>/.workspace/tmp/hf-piloto-001/` (não versionados; MP4 ignorado pelo Git). **Nada publicado, agendado ou aprovado** — avaliação estética humana é F13. |
| F13 Avaliação | **Pacote de revisão montado (27/11/2026); aprovação estética pendente do titular.** Pacote portável em `<RAIZ>/.workspace/tmp/hf-piloto-001/revisao/` (não versionado): `review.html` (página única com aviso "MATERIAL DE REVISÃO — NÃO PUBLICADO", seções: post 4:5, carrossel 1:1 ×4, storyboard com 6 frames extraídos por FFmpeg em 2,0/6,0/10,0/14,0/18,0/22,0 s, player do reel, comparação lado a lado **NS-001 v2** × HyperFrames, tabela de relatórios), `post/01-post-agenda-organizada.png` (1080×1350), `carrossel/01…04-*.png` (1080×1080 ×4), `reel/hf-piloto-001-reel.mp4` (**h264 1080×1920, 24,0 s, 30 fps, 0 streams de áudio**) + `hf-piloto-001-narracao-reel.txt`, `frames/01…06-*.jpg` (storyboard), `v2-comparacao/op24-v2-reel-instagram.mp4` (**NS-001 v2**, Resultado 08, PR #33 — **corrigido em HF-002: NÃO é Op24**; **h264 1080×1920, 47,0 s, 30 fps, 0 streams de áudio**, sha `63bef7c1…360b11b` conferido contra o INDICE-ENTREGA da NS-001 v2; a Op24 v2 é entrega separada de 19 s, sha `208426e2…`, em `.workspace/archives/operacao-resultado-24/delivery-v2-completa.zip` — divergência declarada, não escondida), `qc/re-render-timing.mp4` + `re-render-timing.json`/`-wall.txt` (re-render delivery cronometrado: **40,7 s** wall) e três relatórios: `relatorio-tecnico.md` (ffprobe, gates, tempos, checksums SHA-256 de todas as peças), `relatorio-editorial.md` (decisões editoriais + itens que só a revisão humana aprova) e `comparacao-v2-hyperframes.md` (eixos do brief: qualidade visual, animação, preparação, render, recursos, reprodutibilidade). **Determinismo demonstrado:** o re-render cronometrado do reel produziu MP4 **byte-idêntico** à primeira entrega (SHA-256 `572d1390ea9ae0c39b1cd6546f2124445f36d25bb3c77def16abc508b5adcc74` nos dois). Tempo de render do motor legado **não medido** nesta operação (exigiria re-executar a fábrica congelada; número não estimado). **Nenhuma aprovação estética declarada** — o agente não visualiza as mídias; verificação de tipografia, qualidade de imagem, movimento, composição, legibilidade mobile, contraste percebido, áreas seguras, fidelidade ao produto, identidade e coerência entre cenas permanece com o titular/visão sobre o pacote. Nada publicado ou agendado. |
| F14 Testes/CI | **Concluída com ressalvas registradas (27/11/2026).** Suítes do motor HyperFrames verdes com saída real: `renderers/hyperframes/tests/smoke.sh` → **PASS** (h264 1080×1920, 10,0 s, 0 faixas de áudio); `renderers/hyperframes/tests/adapter-smoke.sh` → **PASS** (compose→check→render draft 1080×1920 14,0 s 0 áudio + negativo de guardrails aborta antes do render: "24h" + "agenda sempre cheia"); **novo teste dedicado de determinismo** `renderers/hyperframes/tests/determinism.sh` (fecha a pendência do critério F6) → **PASS**: dois renders draft independentes do mesmo pedido produziram MP4 **byte-idênticos** (SHA-256 `2b4778e6dbc6ae7f0be6f6ed83893665d65aacf1a1cc629c30a06b0388207ff6`) **e** frames-chave extraídos em 2,0/7,0/13,0 s com hashes idênticos (`0484b8f9…`, `1b52cae4…`, `5dfd8698…`), 14 s nos dois. `python tools/run_tests.py --smoke` → **415/416** (104,6 s, 26 módulos); a única falha, `test_publish_pack.PublishPackTest.test_08_resolve_workspace_root`, é **pré-existente e ambiental**: `tools/publish_pack.py` e seu teste estão **inalterados** nesta branch (`git diff` vazio contra a base `3cf2fdc`) e a falha é o comportamento documentado de `resolve_workspace_root` em worktree (resolve o `.workspace` do checkout principal via git-common-dir); mesmo 415/416 "falha ambiental pré-existente" registrado na operação v2.8 (HANDOFF). `npm test` (platform) → **1017 testes: 1009 pass, 1 fail, 7 skipped**; a falha (`output-plan-examples`: allowlist do projeto exemplo contém `instagram-feed-image-portrait`/`facebook-feed-image-portrait` além dos cinco planos versionados) foi **introduzida pela base** no commit `f01ed60` (Op 24, ancestral do ponto de ramificação `3cf2fdc` — provado por `git merge-base --is-ancestor` e `git diff 3cf2fdc HEAD` vazio nos dois arquivos): **não é regressão do HF-001**; correção pertence à linha Op 24–26 (PR #35) ou autorização própria — registrada como dependência para o CI verde dos PRs C/D. Gates legados preservados: nada do HF-001 toca `platform/src` nem os workflows ativos; provas de fila verde re-executadas após o F12 (`ci_hyperframes_queue_proof.py` positivo/guardrails/recuperação, ZIP sha `dc30404b…e7176da`; `ci_studio_queue_proof.py` 5/5 completed na F7/F8). **Novo gate HyperFrames proposto como workflow rascunho:** `.github/workflows/hyperframes-validation.yml` — dispara **somente por `workflow_dispatch`** (não roda em push/PR; nenhum workflow ativo alterado), matriz ubuntu+windows, runtime pinado 0.9.103 + build da ponte `platform/dist` + os três smokes + prova de stills com os pedidos versionados do piloto (PNG 1080×1350/1080×1080 codec png) + prova da fila (porta 8813) + invariante de mídia fora de `.workspace/`; YAML validado com parse real (js-yaml, cache npm confinado em `<RAIZ>/.workspace/tmp/hf001/`). Promoção do trigger a push/PR é decisão do titular na integração (F18). |
| F17 Segurança | **Concluído (27/11/2026, varreduras com saída real).** (1) Confinamento de caminhos no adaptador: `workdir`/`out` e mídias validados contra escape de `<RAIZ>` (`ASSET_PATH_ESCAPE`, `PATH_ESCAPE`) — provado no F6 (critério de aceite marcado). (2) Varredura de segredos (`grep -rniE` de api key/secret/password/bearer/AKIA/ghp_/sk-) sobre o código novo do HF-001 (`renderers/hyperframes/{adapter,config,scripts,tests}/`, `package.json`, `tools/render_hyperframes.py`, `tools/render_hyperframes_still.py`) → **nenhuma correspondência**; sobre os arquivos versionados do piloto (`02-reels-shorts/hf-piloto-001-organizacao-agenda/`, `04-legendas/hf-piloto-001-narracao-reel.txt`) → **nenhuma correspondência**; sobre os artefatos de entrega em `.workspace/tmp/hf-piloto-001/{entrega,revisao}/` (JSON/TXT/MD/HTML) → **nenhuma correspondência**. (3) Ausência de comandos de nuvem: varredura por `hyperframes publish|cloud|auth|lambda|cloudrun` e endpoints HeyGen no código novo → única correspondência é a declaração `$schema` (namespace do schema, não chamada) em `adapter/compose.mjs`; nenhum comando de nuvem/login executado na operação. (4) Entrega sem segredos: ZIPs das provas de fila verificados contêm somente `primary-output.mp4` + `narration.txt` (sem `.srt`, sem credenciais); snapshot da fila congela `tenantId` (guardrails por marca). (5) Telemetria desabilitada + `HYPERFRAMES_SKIP_SKILLS=1` (F3); caches confinados pós-incidente (F3). |
| F18 PRs/relatório | **Concluída com bloqueio registrado (27/11/2026).** Branch `codex/hyperframes-core-migration` enviada ao remoto com 9 commits de fase + commit de fechamento; **sem merge**. Mapeamento PR A/B/C/D por faixa: PR A docs = `3fca35a`; PR B fundação = `89ef85f`+`5d4465c`; PR C integração = `d2442bc`+`8ceb8d5`; PR D produção = `f06c355`+`eabb13c`+`19d8430`+`51679c6`+fechamento. **Bloqueio:** `gh` ausente na estação (`command not found`, exit 127) e sem `GITHUB_TOKEN` — PRs não criáveis como objetos do GitHub; link manual registrado: `https://github.com/Jonatasbottaro/marcasalao-marketing/compare/main...codex/hyperframes-core-migration?expand=1`. PRs pré-existentes #33/#34/#35 intocados. Relatório master A–AD versionado em [RELATORIO-MASTER.md](RELATORIO-MASTER.md) (30 seções, status por fase, evidências; nota metodológica: títulos exatos das seções do briefing não recuperáveis — anexo excluído — estrutura reconstruída). Handoff AGENTS.md entregue no retorno final da sessão. |
## HF-003.5 — Concorrência da fila, seletor visual e exportação HyperFrames pela interface (28/11/2026)

Seção aditiva da continuidade HF-003.5 (branch `codex/hyperframes-core-migration`,
worktree `<RAIZ>/.workspace/worktrees/hf001`; **sem merge, deploy ou publicação**).
Cinco estados que **não se confundem** e são mantidos separados nesta seção:

1. **Backend HyperFrames funcionando** — provado (F6/F7/F8 e as três provas HTTP abaixo).
2. **Frontend do Studio funcionando** — provado (HF-003.4, seletor visual incluído).
3. **Integração visual do HyperFrames funcionando** — provada agora (seletor "Motor"
   grava `renderer.adapter` e o export passa a usar o motor escolhido).
4. **Exportação HyperFrames comprovada pela interface** — provada agora (trabalho novo
   criado, renderizado, revisado e empacotado só por controles visuais).
5. **Qualidade estética** — **pendente do titular**; nada aqui é aprovação estética.

### 1. Concorrência e integridade da fila

Prova dedicada nova: `tools/ci_hyperframes_concurrency_proof.py` (banco de fila
isolado por `STUDIO_QUEUE_DB_PATH` em `<RAIZ>/.workspace/tmp/hf003-concurrency/`,
removido no `finally`; não toca a fila de produção existente). Execução real:

```
python tools/ci_hyperframes_concurrency_proof.py --port 8821
hyperframes-concurrency CI HTTP proof ok
{"batchId": "batch-b8d4644130",
 "counts": {"total": 2, "queued": 0, "running": 0, "completed": 2, "failed": 0,
            "cancelled": 0, "interrupted": 0, "batchStatus": "completed"},
 "cancelledItemId": "item-81536d1994", "cancelBatchId": "batch-622712d2eb",
 "runBatchId": "batch-2fa9c5085e",
 "deliveryDirs": [".workspace/studio/works/ci-conc-alpha-220816/deliveries/hyperframes",
                  ".workspace/studio/works/ci-conc-beta-220816/deliveries/hyperframes"],
 "adapters": ["hyperframes", "hyperframes"], "snapshotRendererCount": 2}
```

Cobertura asserida (não declarada): dois trabalhos submetidos **simultaneamente** por
duas threads com a mesma `idempotencyKey` → **um único lote** e exatamente uma
resposta `deduplicated`; **executor único em serie** por workspace (lease obtida pelo
processo e **negada** a um segundo `StudioQueue` rival); **1 tentativa por item**
(total de tentativas = 2, sem retentativa silenciosa); **isolamento** (dois
`outputDir` distintos, ambos `hyperframes`); **cancelamento de item pendente**
(`CANCELLED_BY_USER`, lote converge com 1 cancelado) e **recusa de cancelamento de
item em execução** (HTTP 400 contendo `running`); **sem fallback silencioso**
(manifesto declara `adapter: hyperframes`, `renderer.adapter: hyperframes`,
`captionsMode: clean`, artefato `video` presente e **sem SRT**); **registro do
renderizador efetivo** (snapshot congelado em SQLite declara
`renderer.adapter = hyperframes`, `tenantId = marca-salao`, `captionsMode = clean`
nos 2 itens).

Regressão das demais provas, reexecutadas na mesma árvore após as alterações:

- `python tools/ci_hyperframes_queue_proof.py --port 8822` → `hyperframes-queue CI HTTP proof ok`
  (`positiveBatch batch-ef27512cf1`, `guardrailsBatch batch-496a9658c3`,
  `recoveryBatch batch-25d7dd713c`, `zipSha256 33a5ec90…06303d9`).
- `python tools/ci_studio_queue_proof.py --port 8823` → `studio-production-queue CI HTTP proof ok`
  (lote `batch-3339a9b744`, **5/5 completed**, `zipSha256 65b0adfc…8159`).

A fila de produção (`<RAIZ>/.workspace/studio/production-queue.sqlite`) **não foi
destruída nem recriada**: 51 itens preservados (35 completed, 15 failed, 1 cancelled,
0 interrupted) antes e depois das provas.

### 2. Seletor visual do motor (fecha a lacuna do HF-003.4)

A interface não tinha seleção explícita de motor. Menor melhoria necessária, no shell
`tools/studio/` (as ilhas React não têm esse controle):

- `tools/studio/index.html` — `<select id="work-renderer-select">` na barra do trabalho
  ativo, com as opções **HyperFrames** e **FFmpeg (legado)**.
- `tools/studio/app.js` — `renderActiveWorkBar()` reflete o adapter salvo (default de
  **exibição** `hyperframes`, nunca regravado automaticamente) e o handler de `change`
  grava via `POST /api/works/renderer/save`, com reversão do valor em caso de erro.
- `tools/studio/style.css` — layout do controle (`.work-renderer-toggle`, `.renderer-select`).

Comportamento observado no navegador (navegador interno do Qoder; painel não visível,
portanto **sem captura visual** — ver limitação abaixo): o seletor lê o adapter salvo,
grava a escolha, persiste `{"adapter": "hyperframes"}` em `work.json` e faz o
ida-e-volta hyperframes → ffmpeg → hyperframes. **Nenhum trabalho antigo teve o motor
trocado automaticamente.**

### 3. Exportação HyperFrames comprovada pela interface

Antes desta etapa, `Studio.start_export` ignorava o `renderer` do trabalho e usava
sempre o pipeline FFmpeg — a exportação pela interface não podia produzir HyperFrames.
Correção em `tools/video_studio.py`: com `renderer.adapter == 'hyperframes'` e
`kind == 'video'`, o export passa a chamar `tools/render_hyperframes.py`. **Nenhuma
exportação FFmpeg foi usada como prova.**

Fluxo executado **inteiramente por controles visuais** (cliques e `change` reais no
DOM; chamadas HTTP internas apenas como efeito das ações da interface):

1. Novo trabalho `hf005-interface-proof-v2` criado no formulário "Criar novo trabalho"
   (nome, id, projeto `marca-salao`, modelo fictício Marca Salão).
2. Motor selecionado no seletor visual → **HyperFrames**; trabalho salvo.
3. Perfil `instagram-reels-video` marcado na tabela de destinos; 3 cenas do modelo
   salvas; **prévia da montagem** gerada (`540×960 · 14.00s · 235513 bytes · sem áudio`).
4. Exportação em lote: seleção do trabalho na tabela → modal "Exportar em lote" →
   apenas **HyperFrames / Reels do Instagram (HyperFrames)** marcado → pré-voo
   `2 destino(s) pronto(s), 0 bloqueado(s)` → confirmar → `Lote batch-385742860e
   enfileirado (2 peça(s))`.
5. Render concluído (`item-6c1ce75351`, `completed`, `hyperframes`,
   `instagram-reels-video`).
6. Revisão: peça HyperFrames exibida como `Render concluído — aguardando revisão`
   (`1080×1920 · 30 fps · 14.0s · 0 áudios · versão hyperframes-instagram-reels-video-v1-af2dd898
   · MP4 sha256 c562d46680`) → **Aprovar para entrega local** (`Decisão de revisão
   registrada`).
7. **Gerar ZIP de entrega** → `Pacote ZIP de entrega pronto para download`
   (`/api/works/package/download?id=hf005-interface-proof-v2`), conteúdo real:
   `hyperframes/instagram-reels-video/primary-output.mp4` (416.693 bytes),
   `narration.txt`, `briefing/ficha-editorial.{json,txt}`, `package-manifest.json`.

Manifesto de entrega verificado (`delivery-manifest.json`):

| Campo | Valor |
| --- | --- |
| `adapter` / `renderer.adapter` / `renderer.engine` | `hyperframes` / `hyperframes` / `hyperframes` |
| `captionsMode` | `clean` |
| `artifacts.video.sha256` | `c562d4668098ab0f0134f55a1d76dc144d07c19163173448806af78cb9573fd3` |
| `artifacts.video.bytes` | 416.693 |
| `ffprobe` do manifesto | 1 stream de vídeo, **0 de áudio**, `h264`, 1080×1920, 30,0 fps, `yuv420p`, 14,0 s |
| `artifacts.narration` | `.txt` (416 bytes, sha `ef8f878f…80181d`) |
| `artifacts.srt` | **ausente** (VIDEO CLEAN) |

`ffprobe` independente (binário portátil do projeto, `.workspace/tools/ffmpeg/ffprobe.exe`)
confirmou: 1 stream `h264` 1080×1920 `30/1`, `duration 14.000000`, **nenhum stream de
áudio**. SHA-256 do arquivo conferido: `c562d4668098ab0f…9573fd3`.

### 4. Persistência após reinício

Backend interrompido (`taskkill //F //PID 12332`) e reiniciado
(`python tools/video_studio.py --port 8765`, PID 14380; `/api/hyperframes/readiness`
→ `{"ok": true, "version": "0.9.103", "adapter": "hyperframes"}`). Após recarregar a
página: o trabalho `hf005-interface-proof-v2` reaparece na tabela de recentes, "Reabrir"
restaura a barra do trabalho com **Motor: HyperFrames**, e a fila reabre com
**0 running / 0 interrupted** (recuperação de startup não precisou classificar nada).

### 5. Limitação registrada

O navegador interno do Qoder respondeu `NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`
(viewport 0×0, painel não exibido), o que impede cliques de ponteiro e captura de
tela. Todas as ações acima foram executadas por script no DOM (clique em botão real,
definição de `value` + `change` em `select`/`input`) e verificadas por snapshot
estrutural e leitura de estado. **Isso é teste estrutural do fluxo, não aprovação
estética** — a aparência, tipografia, movimento e legibilidade permanecem com o titular.

### 6. Limpeza e preservação

- Projetos de CI residuais removidos: `.workspace/studio/projects/ci-conc-*.project.json` (32 arquivos).
- Diretórios de trabalho de CI removidos: `ci-conc-alpha-214432`, `ci-conc-alpha-214630`, `ci-conc-dbg4`.
- Banco de fila isolado e log de reinício removidos (`.workspace/tmp/hf003-concurrency/`, `.workspace/tmp/hf005-studio-restart.log`).
- Preservados: fila de produção, `demo-marca-salao{,-2,-3}`, `hf002-studio-proof`, `ci-hf-queue-work`, `ci-conc-alpha-220816`/`ci-conc-beta-220816` (evidência da prova de concorrência) e `hf005-interface-proof{,-v2}`.
- Nada publicado, agendado ou integrado à `main`.
