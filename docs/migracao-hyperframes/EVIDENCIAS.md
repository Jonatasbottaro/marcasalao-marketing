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
| F7/F8 Studio+fila | _pendente_ |
| F9/F10 Templates | _pendente_ |
| F12 Piloto | _pendente_ |
| F13 Avaliação | _pendente_ |
| F14 Testes/CI | _pendente_ |
| F17 Segurança | _pendente_ |
| F18 PRs/relatório | Branch `codex/hyperframes-core-migration` enviada ao remoto até `3fca35a` (27/11/2026). PR da branch **pendente de criação**: `gh` ausente e sem token na estação; link manual: `https://github.com/Jonatasbottaro/marcasalao-marketing/compare/main...codex/hyperframes-core-migration?expand=1`. Relatório master A–AD ao final da operação. |
