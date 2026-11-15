# Registro de aceite — Modelos reutilizáveis e variações em série no Video Studio (2026-11-15)

## Escopo entregue

- **Branch técnica**: `codex/studio-work-templates-v1` (sobre `main` em `801025aceeb444dadb75c688f4a4498f2af3019a`, merge da PR #12).
- **Fechamento do snapshot da fila (`tools/studio_queue.py`)**:
  - Snapshot `schemaVersion: 2` congela também os bytes do `ProjectManifest` (`projectManifestSha256`).
  - A tentativa isola os insumos verificados no staging (`frozen/project.json`, `frozen/media/`), reconfere cada SHA-256 após a cópia e aponta o pedido para as cópias isoladas: o render consome exatamente os bytes conferidos; mudança na origem entre a conferência inicial e o render usa a cópia isolada ou falha antes de promover.
  - Erros acionáveis por peça: `MEDIA_DIVERGENCE`, `PROJECT_DIVERGENCE` (com `canUseCurrent: true` e oferta de enfileirar a versão atual).
  - Itens pendentes legados (snapshot v1 sem `projectManifestSha256`): falham com `SNAPSHOT_LEGACY` e exigem **Enfileirar versão atual**; nenhum item legado é renderizado com a garantia antiga.
  - A Revisão continua vinculando a entrega à versão que entrou na fila: editar apenas o rascunho marca `draft_outdated` sem alterar o snapshot vinculado (`requestSnapshot` preservado).
- **Modelos e variações (`tools/studio_templates.py` + rotas em `tools/video_studio.py` + UI em `tools/studio/{index.html,app.js}`)**:
  - Armazenamento em `.workspace/studio/templates/<id>/` com revisões imutáveis (`revisions/rev-N/snapshot.json` + `media/` copiada e conferida por SHA-256, deduplicada por hash entre modalidades); restrição ao projeto de origem na V1.
  - **Salvar como modelo** captura vídeo/carrossel/Motion (cortes, `framingByProfile`, destinos, estilos, efeitos), ficha editorial e textos como campos editáveis, mídias com origem/licença/SHA-256; detecção de edição concorrente (`TEMPLATE_CAPTURE_CONFLICT`); promoção da revisão como unidade.
  - **Duplicar como rascunho** usa o mesmo serviço de instanciação sem modelo permanente.
  - **Criar a partir de modelo**: plano por linha sem criar arquivos (`POST /api/templates/plan`), confirmação transacional idempotente (`POST /api/templates/create`) com retomada de linhas falhas; colisão de ID, mídia ausente/divergente e mudança de allowlist preservam o existente e são reportadas por linha.
  - Instanciação com IDs próprios, `requestId` do Motion ajustado, caminhos de mídia reescritos, referências internas preservadas, ficha própria, revisão em aberto, entregas vazias; revalidação de catálogo/allowlist/capacidade local (`PROFILE_NEEDS_ADJUSTMENT`).
  - Lista de variações com **Abrir trabalho** e **Enviar para a Fila de Produção**, reutilizando planejamento/confirmação da fila existentes.
- **Provas**: `tools/tests/test_studio_templates.py` (6 testes), `tools/tests/test_queue_process_restart.py` (2 testes de processo com reinício real), `tools/ci_studio_templates_proof.py` (prova HTTP integrada ao workflow de render local).

## Evidências executadas

Estação Windows (Node 22.23.2 WinGet, Python 3.14, FFmpeg/FFprobe no PATH), worktree `<RAIZ>/.workspace/worktrees/studio-work-templates-v1`, branch `codex/studio-work-templates-v1` sobre `801025a`. Logs locais em `<RAIZ>/.workspace/logs/studio-work-templates-v1/` (não versionados; reprodução pelos comandos abaixo).

### Gates da platform (sem mudanças em `platform/` nesta rodada)

- `npm run build` + `npm run typecheck`: exit 0.
- `npm test`: **994/994** (`pass 994`, `fail 0`, `skipped 0`).
- `npm run test:contracts`: **324/324** (`pass 324`, `fail 0`, `skipped 0`).

### Suítes Python focadas (REQUIRE_RENDER=1)

- `tools/tests/test_studio_queue.py`: **6/6** (inclui `test_05_project_divergence_and_frozen_bytes` — origem alterada após o isolamento usa os bytes originais, hash da fonte no manifesto igual ao congelado — e `test_06_legacy_pending_snapshot_requires_current_version`).
- `tools/tests/test_queue_process_restart.py`: **2/2** — processo real do Studio encerrado e reiniciado: (a) queda durante o render com item pendente → `interrupted` + entrega válida anterior preservada + pendente retoma e conclui; (b) produtor órfão promove após a morte do servidor → reinício reconcilia pelo `attemptId`, item `completed` e **uma única versão** na Revisão (reconciliar de novo não duplica).
- `tools/tests/test_studio_templates.py`: **6/6** — captura/revisões imutáveis/instanciação da revisão antiga; plano sem arquivos + overrides + idempotência + retomada com condição resolvida + recusa de reuso de chave; colisão/mídia ausente/allowlist/projeto de origem; duplicação + reinício; edição concorrente; variação → fila → FFprobe → Revisão → ZIP.

### Prova HTTP de CI (`python tools/ci_studio_templates_proof.py --port 8804`)

Exit 0. Resumo: modelo `modelo-agenda-ci` com `rev-1`/`rev-2`; variações `ci-tpl-var-1..3` criadas da `rev-1` (título/herança conferidos); duplicação `ci-tpl-dup-work`; colisão de ID, mídia ausente, allowlist alterada e modelo de outro projeto recusados; lote `batch-f4ca9da13b` **4/4 completed** (Reels, YouTube horizontal, Motion vertical, carrossel 4:5); reexportação isolada do horizontal preservando o hash do Reels; FFprobe `1080x1920`/`1920x1080` @ `30/1` com **0 faixas de áudio** e carrossel `1080x1350`; aprovação na Revisão + ZIP `zipSha256 ce8fc9202d21234f745eda992656bf8a857fe5afe10df2dbaeb6b73cbc9e4aca` com manifesto/hashes/versão conferidos; recuperação após reinício do servidor.

### Aceite em Chromium real (Playwright, `http://127.0.0.1:8805`)

Capturas em `.workspace/logs/studio-work-templates-v1/browser/` (01-home-modelo, 02-plano-variacoes, 03-fila-concluida, 04-revisao-zip, 05-pos-reinicio):

1. Trabalhos fictícios das duas marcas no mesmo Studio (`e2e-tpl-ms` com gravação recortada `sourceStartMs=250`, `framingByProfile` vertical/horizontal; `e2e-tpl-mh`).
2. **Salvar como modelo** pela UI → `modelo-agenda-e2e` `rev-1`; edição do título da origem + **nova revisão** (`rev-2`, `rev-3`).
3. **Criar a partir de modelo** → `rev-1` + 3 linhas (`e2e-var-1..3`): plano mostrou "pronta" por linha com resumo herdado/override sem criar arquivos; confirmação criou as 3 com `origin.revisionId=rev-1`.
4. Independência: título editado só em `e2e-var-1`; `e2e-var-2` mantém o próprio override; `e2e-var-3` herda o título da `rev-1` (≠ título atual da origem); gancho override em var-1 e herdado em var-3; cortes/enquadramento da `rev-1` preservados; revisão em aberto (0 versões).
5. **Duplicar como rascunho** do trabalho MTH → `e2e-mh-copia` (`origin.kind=duplicate`, mídias na pasta do novo trabalho).
6. **Enviar para a Fila de Produção** pela lista de variações (var-4) abriu o modal de lote existente com só aquele trabalho; lote `batch-218d78f7b4` **4/4**; lote misto `batch-c7e35942ab` (var-1 Reels+horizontal+Motion, var-2 carrossel 4:5) **4/4**; aba Fila mostrou **Total 8 / Concluídos 8 / Falhos 0**.
7. FFprobe dos promovidos: `1080x1920@30/1`, `1920x1080@30/1`, Motion `1080x1920@30/1`, **0 áudio**; carrossel `1080x1350`.
8. **Revisão & Entrega**: aprovação explícita do Reels de var-1 + **Gerar ZIP** → `zipSha256 b6ff80663e64a1f4d10453c4afaae02061594a6916d59af2cc7c8f854ca84187`, 5 arquivos com hashes conferidos contra os bytes do ZIP, `deliveryVersionId video-instagram-reels-video-v1-ac367e4b` (mesma versão da fila), ficha com gancho da variação.
9. **Reinício do servidor** + reload: 3 revisões, título editado da var-1, corte 250 ms, fila 8/8, ZIP disponível e duplicação preservados.

### Suíte Python completa e CI

- **Suíte Python completa** (`python -m unittest discover -s tools/tests -v`, `REQUIRE_RENDER=1`, Node 22 no PATH): **243/243 testes OK**, zero falhas, zero erros, zero skips, em `2293.647s` (log `python-suite-full-2.log`; inclui `test_studio_templates.py` 6/6, `test_studio_queue.py` 6/6 e `test_queue_process_restart.py` 2/2). A primeira corrida (`python-suite-full.log`) preservada com o diagnóstico de portabilidade abaixo.
- **Workflows no SHA apropriado**: no checkpoint `801025a` rodou apenas `Validar render local de prova` (run [43685212351](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43685212351), Ubuntu+Windows verdes); `Validar contratos da platform` tem filtro de paths em `platform/**` e seu último verde é `cfb0e62` (run [43671676275](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43671676275)) — esta rodada não altera `platform/`, e os contratos foram conferidos localmente (324/324).
- **CI do PR #13**: run [43718452517](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43718452517) no SHA `043c58d` — `ubuntu-latest · render real` e `windows-latest · render real` **success** (inclui a etapa nova `Prova de modelos reutilizaveis e variacoes em serie (Studio HTTP)`); run intermediário [43717325695](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43717325695) em `c0b87fa` também verde nos dois sistemas.
- **Merge**: PR #13 integrada na `main` pelo merge commit `3f4600b186465356d7b1699080a9e22b3fe5f028`; CI pós-merge run [43721903973](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43721903973) **success** em `ubuntu-latest · render real` e `windows-latest · render real`.

### Diagnóstico de gate falho na primeira corrida (preservado)

A primeira corrida da suíte completa nesta worktree (`python-suite-full.log`) acusou 3 falhas que **não eram regressões de código**: `test_render_local.test_08/08b` (mocks de promoção comparavam o caminho de staging sem o prefixo `\\?\` que `render_local.fs_path` aplica a partir de 248 chars) e `test_recording_cuts.test_render_real_cortes_precisos_entre_keyframes` (`open()` simples de SRT com caminho de 263 chars, acima do MAX_PATH do Windows; a exportação em si havia concluído). Em worktrees aninhadas o prefixo do caminho cresce e cruza o limite; no checkout principal e no CI (caminhos curtos) os testes passavam. Correção de portabilidade nos próprios testes (commit `043c58d`): normalização do prefixo nos mocks e `fs_path` na leitura do SRT; os 3 testes reexecutados isolados passaram (134 s) e a suíte completa foi relançada (`python-suite-full-2.log`).