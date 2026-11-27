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

## F5–F18 — Pendentes de evidência

Cada fase registra aqui sua evidência ao concluir (critérios em
[CRITERIOS-DE-ACEITE.md](CRITERIOS-DE-ACEITE.md)). Nada é pré-marado: campos abaixo
são preenchidos somente com saída de comando real.

| Fase | Evidência |
| --- | --- |
| F6 Adaptador | **Concluído (27/11/2026).** `renderers/hyperframes/adapter/` (`tenant.mjs`, `compose.mjs`, `hf_adapter.mjs`) + `scripts/hf-adapter.sh` + entrada Python `tools/render_hyperframes.py`. Smoke `tests/adapter-smoke.sh` verde: pedido real de exemplo → composição → `check` → render draft → `ffprobe` **h264 1080×1920, 14,0 s, 0 streams de áudio**; caso negativo: caption "Agenda sempre cheia, 24h sem faltas" aborta antes do render com `GUARDRAILS_VIOLATION` (termos "24h" + "agenda sempre cheia"). Decisão CLI × API: **CLI pinado** (spawn de `hyperframes/bin/hyperframes.mjs`); `@hyperframes/producer` avaliado (expõe `createRenderJob`/`executeRenderJob` + `ProgressCallback`) e mantido como opção para progresso fino na fila (F8). Determinismo por re-render com hash de frames: pendente de teste dedicado (F14). |
| F7/F8 Studio+fila | **Concluído (27/11/2026).** Modalidade `hyperframes` aditiva na fila SQLite existente (mesmos estados/recovery; sem fallback silencioso — MKT-VIDEO-003): seleção explícita de motor por trabalho (`renderer.adapter`, rotas `/api/works/renderer/save`, `/api/hyperframes/readiness`, `/api/works/hyperframes/preview`), opção de plano + preflight (ffmpeg/ffprobe + runtime HF), executor delegando ao `tools/render_hyperframes.py` em modo de entrega (`--output-dir/--staging/--attempt-id/--fence-file`, mesmo contrato `delivery-manifest.json` da fila com `captionsMode: clean`), snapshot congelando `tenantId` (guardrails por marca) e `renderer`, entrega em `deliveries/hyperframes/<perfil>/`, peça de revisão `hyperframes:<perfil>` e ZIP reutilizado (`primary-output.mp4` + `narration.txt`, sem SRT). Correção latente junto: `_verify_attempt_promotion` e `_inspect_video_or_motion_piece` exigiam `srt` incondicionalmente — agora respeitam `captionsMode` (vídeo clean legado também beneficia). Prova HTTP `python tools/ci_hyperframes_queue_proof.py --port 8813` verde: lote positivo `batch-8d4235ff77` (ffprobe **1080×1920 @30, 14,0 s, 0 streams de áudio**, peça `pending_review` → aprovação → ZIP sha `daea8cbc…f6e05a10` sem `.srt`); negativo `batch-2f4add154a` (caption "Agenda sempre cheia, 24h sem faltas" → item `failed` com `GUARDRAILS_VIOLATION`, sem reprocesso FFmpeg); recuperação `batch-9927ceeff3` (item `running` forjado → `recover_on_startup` → `interrupted`/`INTERRUPTED_INCONCLUSIVE` → `/api/queue/retry` → `completed`). Regressão das modalidades legadas na mesma árvore: `python tools/ci_studio_queue_proof.py --port 8803` verde — lote `batch-f6eb82af45` com **5/5 completed** (vídeo ×2, carrossel, motion, vídeo), ZIP sha `e023dacc…5a55174e5`. |
| F9/F10 Templates | **Concluído (27/11/2026).** Biblioteca de templates dentro do compositor (`adapter/compose.mjs`), selecionada pelo campo neutro do contrato `profile.beatPlan.beats[].narrativeFunction` (o `kind` legado existia só na fábrica congelada; `platform/src` intocado): `hook`→card de marca centrado, `demonstration`→captura como estrela com texto na base sobre scrim suave, `cta`→convite centrado sem aparência de botão (frame.md); layout genérico por geometria com `data-resolution: square` corrigido no 1:1. Provas com `tools/render_hyperframes.py` (pedido exemplo 3 beats hook/demonstration/cta): reel 9:16 `instagram-reels-video` → veredito ok, **h264 1080×1920, 14,0 s, 0 streams de áudio**, 3 beats; horizontal 16:9 `youtube-video-horizontal` → **h264 1920×1080, 14,0 s, 0 streams de áudio**. Stills (F10) pela captura oficial `hyperframes snapshot` (`hf_adapter.mjs --still`, exige 1 PNG + ffprobe codec `png`/geometria) com ferramenta `tools/render_hyperframes_still.py` sobre `CarouselRequest v1` (catálogo+allowlist via ponte; entrega transacional `01-<id>.png`… + `stills.zip` + `still-manifest.json` + `index.json`): 4:5 `instagram-feed-image-portrait` → 3 PNGs **1080×1350 codec png**; 1:1 `instagram-feed-image-square` → 3 PNGs **1080×1080 codec png** (ffprobe conferido em todos). Negativo still: card "Agenda sempre cheia, 24h sem faltas" → `GUARDRAILS_VIOLATION` (termos "24h" + "agenda sempre cheia") **antes da captura**, sem entrega parcial (diretório do pedido negativo não criado; entrega anterior intacta). Fallback preservado: `produce_carousel.py` e ComfyUI08 intocados. Regressão da fila com o novo compositor: `python tools/ci_hyperframes_queue_proof.py --port 8813` verde (`exit=0`) — positivo `batch-a940affe98`, guardrails `batch-88415b1d4b`, recuperação `batch-6fb3a53340`, ZIP sha `36d8571d…adfd9`. Avaliação estética humana é F13 (nada aprovado sem ver). |
| F12 Piloto | _pendente_ |
| F13 Avaliação | _pendente_ |
| F14 Testes/CI | _pendente_ |
| F17 Segurança | _pendente_ |
| F18 PRs/relatório | Branch `codex/hyperframes-core-migration` enviada ao remoto até `3fca35a` (27/11/2026). PR da branch **pendente de criação**: `gh` ausente e sem token na estação; link manual: `https://github.com/Jonatasbottaro/marcasalao-marketing/compare/main...codex/hyperframes-core-migration?expand=1`. Relatório master A–AD ao final da operação. |
