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
- [ ] Mesmo pacote + mesma versão → mesmo output (determinismo; verificação por
      re-render com hash de frames-chave) — teste dedicado no F14.
- [x] Decisão registrada: API `@hyperframes/producer` vs CLI — **CLI pinado**
      (caminho único check+render, isolamento de processo); producer avaliado e
      mantido como opção de progresso fino para a fila (F8).

## Studio e fila (F7/F8)

- [ ] Submeter job HyperFrames pelo Studio cria item `queued` na fila existente.
- [ ] Progresso e logs visíveis; estados `running/completed/failed` exercitados.
- [ ] Matar o processo em `running` e reiniciar o Studio recupera o item
      (`recover_on_startup`) sem perder os demais.
- [ ] Limite de concorrência respeitado (1 render HyperFrames por vez na estação).
- [ ] Pacote de entrega final contém MP4 + TXT de narração; SRT ausente por padrão.

## Templates e formatos (F9/F10)

- [ ] Templates nativos cobrem: reel produto/funcionalidade/institucional, motion,
      horizontal 16:9, post 4:5/1:1, carrossel, CTA/endcard.
- [ ] Cada template passa `check` + snapshot de meio de cena legível.
- [ ] Geometrias exatas dos perfis (1080×1920, 1920×1080, 1080×1080, 1080×1350).
- [ ] Nenhuma claim proibida nos textos; headerOverlay presente em todo o vídeo;
      áreas seguras respeitadas no 9:16.

## Campanha piloto (F12)

- [ ] HF-PILOTO-001-MARCA-SALAO entregue: post 1080×1350, carrossel 4 cards,
      reel 20–25 s 1080×1920 com animações nativas.
- [ ] Capturas reais do Meu Salão (dados fictícios, Studio Bella) usadas nas cenas
      de interface; identidades MKT-BRAND-001 respeitadas.
- [ ] `direcao-de-cenas.md` + `narracao-reel.txt` (tempos, PT-BR) prontos para
      gravação externa.
- [ ] `ffprobe` de cada vídeo: 0 streams de áudio; duração/geometria conforme plano.
- [ ] Nada publicado/agendado; entrega para em revisão humana (F13).

## Avaliação e comparação (F13)

- [ ] Pacote de revisão portável (prévias estáticas + storyboard + player) entregue
      dentro de `<RAIZ>`.
- [ ] Comparação Op24 v2 × HyperFrames documentada com frames lado a lado.
- [ ] Nenhuma aprovação estética declarada sem visualização humana registrada.

## Testes e CI (F14)

- [ ] `python tools/run_tests.py --smoke` verde na branch da migração.
- [ ] `npm test` (platform) verde na branch da migração.
- [ ] Smoke HyperFrames (`renderers/hyperframes/tests/smoke.sh`) verde.
- [ ] Gates legados (CI existente) continuam verdes — nada quebrado.
- [ ] Novo gate HyperFrames proposto como workflow draft, sem alterar os ativos.

## Entrega (F18)

- [ ] PRs A/B/C/D abertos como **rascunho**; nenhum merge para `main`.
- [ ] Relatório master A–AD com status por fase e evidência.
- [ ] Handoff AGENTS.md completo, incluindo a confirmação textual de confinamento
      em `<RAIZ>`.
- [ ] `git status --short` limpo de surpresas; worktrees temporárias removidas ou
      justificadas; `.workspace/` sem única cópia de arquivo permanente.
