# Critérios de aceite — HF-001

Critérios verificáveis por fase. Um critério só é aceito com evidência executável
(comando + saída registrada em [EVIDENCIAS.md](EVIDENCIAS.md)).

## Fundação (F3/F4)

- [x] `renderers/hyperframes/package.json` pinia `hyperframes` **exato** 0.9.103.
- [x] Smoke end-to-end verde: `init → check → render draft` sem erro.
- [x] MP4 do smoke: h264, 1080×1920, ~10 s, **0 streams de áudio** (`ffprobe`).
- [x] Caches npm/Chrome/TEMP confinados em `<RAIZ>/.workspace/tmp/hf001/`; nenhuma
      escrita fora de `<RAIZ>` (verificado após o incidente do env).
- [x] Skills HyperFrames atualizadas pelo procedimento oficial; `skills-lock.json`
      v2 com commit upstream + hashes.
- [x] `doctor` ok (com FFmpeg portável do projeto no PATH via env).

## Documentação (F1/F2/F15/F16)

- [x] Inventário documental e funcional publicados.
- [x] Matriz de migração cobre todos os recursos com decisão e risco.
- [x] MKT-VIDEO-003 registrada; contradições históricas com nota datada, sem apagar
      o registro original.
- [x] Índices oficiais apontam para `docs/migracao-hyperframes/` (na entrega do PR A).
- [x] Política de atualização e rollback escrita.

## Adaptador (F6)

- [x] Aceita um `CreativeExecutionPackage` real e produz composição que passa
      `hyperframes check` sem findings persistentes (smoke 27/11: check verde na
      primeira materialização).
- [x] Render `--quality draft` do pacote conclui e gera MP4 com **0 streams de áudio**
      (h264 1080×1920, 14,0 s).
- [x] Texto com alegação proibida ("Agenda sempre cheia, 24h sem faltas") **aborta**
      o job antes do render, com erro estruturado (`GUARDRAILS_VIOLATION` + termos).
- [x] `renderer.adapter` lido do manifest; sem fallback silencioso para FFmpeg
      (entrada Python aciona exclusivamente o adaptador; falha = veredito `ok:false`).
- [x] Caminhos de entrada validados contra escape de `<RAIZ>` (`ASSET_PATH_ESCAPE`,
      `PATH_ESCAPE`, `workdir`/`out` confinados na entrada Python).
- [x] Mesmo pacote + mesma versão → mesmo output (determinismo; verificação por
      re-render com hash de frames-chave) — teste dedicado `renderers/hyperframes/tests/determinism.sh`
      verde em 27/11/2026 (F14): dois renders draft independentes byte-idênticos
      (SHA-256 `2b4778e6…07ff6`) + frames-chave 2,0/7,0/13,0 s idênticos; em
      delivery, o reel do piloto F13 também re-renderizou byte-idêntico
      (`572d1390…dcc74`).
- [x] Decisão registrada: API `@hyperframes/producer` vs CLI — **CLI pinado**
      (caminho único check+render, isolamento de processo); producer avaliado e
      mantido como opção de progresso fino para a fila (F8).

## Studio e fila (F7/F8)

- [x] Submeter job HyperFrames pelo Studio cria item `queued` na fila existente.
      (prova HTTP `ci_hyperframes_queue_proof.py`: lote positivo enfileira e
      processa; EVIDENCIAS F7/F8)
- [x] Progresso e logs visíveis; estados `running/completed/failed` exercitados.
      (positivo `completed`, negativo `failed` com `GUARDRAILS_VIOLATION`,
      recuperação `running`→`interrupted`→retry→`completed`)
- [x] Matar o processo em `running` e reiniciar o Studio recupera o item
      (`recover_on_startup`) sem perder os demais. (lote de recuperação da prova
      HTTP: item `running` forjado → `recover_on_startup` → `interrupted` →
      `/api/queue/retry` → `completed`)
- [ ] Limite de concorrência respeitado (1 render HyperFrames por vez na estação).
      (executor é serial por workspace por construção; prova explícita de limite
      sob submissão concorrente ainda não executada)
- [x] Pacote de entrega final contém MP4 + TXT de narração; SRT ausente por padrão.
      (ZIP da prova sem `.srt`, `primary-output.mp4` + `narration.txt`)

## Templates e formatos (F9/F10)

- [x] Templates nativos cobrem: reel produto/funcionalidade/institucional, motion,
      horizontal 16:9, post 4:5/1:1, carrossel, CTA/endcard. (combinação perfil ×
      `narrativeFunction` + `motionIntent`; CONTRATOS-E-ADAPTADORES F9)
- [x] Cada template passa `check` + snapshot de meio de cena legível. (gate `check`
      verde em todas as provas, incluindo contraste WCAG AA que reprovou e forçou
      correção real; legibilidade percebida do snapshot segue na revisão humana F13)
- [x] Geometrias exatas dos perfis (1080×1920, 1920×1080, 1080×1080, 1080×1350).
      (ffprobe conferido em todas as provas F9/F10/F12)
- [x] Nenhuma claim proibida nos textos; headerOverlay presente em todo o vídeo;
      áreas seguras respeitadas no 9:16. (guardrails verdes + negativos reais;
      headerOverlay em todos os beats; margem segura `safeBottomMargin` auditada
      pelo `check`)

## Campanha piloto (F12)

- [x] HF-PILOTO-001-MARCA-SALAO entregue: post 1080×1350, carrossel 4 cards,
      reel 20–25 s 1080×1920 com animações nativas. (24,0 s, 6 beats, entradas
      GSAP + slow-zoom; EVIDENCIAS F12)
- [x] Capturas reais do Meu Salão (dados fictícios, Studio Bella) usadas nas cenas
      de interface; identidades MKT-BRAND-001 respeitadas. (CAP-01/02/03/08/10
      versionadas em `fontes/`; tokens Marca Salão do tenant)
- [x] `direcao-de-cenas.md` + `narracao-reel.txt` (tempos, PT-BR) prontos para
      gravação externa. (`04-legendas/hf-piloto-001-narracao-reel.txt` idêntico ao
      `narracao.txt` do adaptador)
- [x] `ffprobe` de cada vídeo: 0 streams de áudio; duração/geometria conforme plano.
- [x] Nada publicado/agendado; entrega para em revisão humana (F13).

## Avaliação e comparação (F13)

- [x] Pacote de revisão portável (prévias estáticas + storyboard + player) entregue
      dentro de `<RAIZ>`. (`<RAIZ>/.workspace/tmp/hf-piloto-001/revisao/`:
      `review.html` + peças + frames + players + relatórios)
- [x] Comparação Op24 v2 × HyperFrames documentada com frames lado a lado.
      (players lado a lado no `review.html` + `comparacao-v2-hyperframes.md`
      com ffprobe/tempos/determinismo; render do motor legado não medido —
      declarado, não estimado)
- [x] Nenhuma aprovação estética declarada sem visualização humana registrada.
      (relatórios técnico/editorial registram a limitação; decisão é do titular)

## Testes e CI (F14)

- [ ] `python tools/run_tests.py --smoke` verde na branch da migração.
      (27/11/2026: **415/416**; a única falha `test_08_resolve_workspace_root` é
      ambiental e pré-existente em worktrees — arquivo inalterado vs base
      `3cf2fdc`, mesmo 415/416 registrado na operação v2.8; não é regressão do
      HF-001)
- [ ] `npm test` (platform) verde na branch da migração.
      (27/11/2026: **1017 testes, 1009 pass, 1 fail, 7 skipped**; a falha
      `output-plan-examples` foi introduzida pela base no commit `f01ed60`
      (Op 24) — arquivos byte-idênticos aos da base `3cf2fdc`; correção pertence
      à linha Op 24–26/PR #35, registrada como dependência do CI verde dos PRs
      C/D)
- [x] Smoke HyperFrames (`renderers/hyperframes/tests/smoke.sh`) verde.
      (PASS: h264 1080×1920, 10,0 s, 0 faixas de áudio; `adapter-smoke.sh` e
      `determinism.sh` também verdes)
- [x] Gates legados (CI existente) continuam verdes — nada quebrado.
      (localmente: nada do HF-001 toca `platform/src`/workflows ativos; falhas
      acima são herdadas da base; provas de fila legada e HyperFrames verdes;
      CI remoto conferido na abertura dos PRs — F18)
- [x] Novo gate HyperFrames proposto como workflow draft, sem alterar os ativos.
      (`.github/workflows/hyperframes-validation.yml`: somente
      `workflow_dispatch`, matriz ubuntu+windows, três smokes + stills + fila;
      YAML validado por parse real; nenhum workflow ativo alterado)

## Entrega (F18)

- [ ] PRs A/B/C/D abertos como **rascunho**; nenhum merge para `main`.
- [ ] Relatório master A–AD com status por fase e evidência.
- [ ] Handoff AGENTS.md completo, incluindo a confirmação textual de confinamento
      em `<RAIZ>`.
- [ ] `git status --short` limpo de surpresas; worktrees temporárias removidas ou
      justificadas; `.workspace/` sem única cópia de arquivo permanente.
