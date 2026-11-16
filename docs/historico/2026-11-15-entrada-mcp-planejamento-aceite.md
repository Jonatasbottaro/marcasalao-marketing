# Aceite — Entrada local por agentes (MCP) no Planejamento do Video Studio

- Data: 2026-11-15
- Branch técnica: `codex/studio-mcp-planning-v1` (base `main` = `516a59d98a8d326c41f1cbff166947338ab56d44`, PR #16 integrada)
- Escopo: servidor MCP pequeno em `tools/`, iniciado pelo cliente via **stdio**, que consulta o briefing de um trabalho e registra propostas `PlanningSuggestion v1` (etapa `creative`) no histórico do Planejamento, para revisão do operador. Duas ferramentas: `consultar_planejamento` e `enviar_proposta`. O Studio continua responsável por leitura, validação e gravação; a interface MCP termina no registro da proposta. Geração de mídia, pesquisa de referências e publicação ficam para outras rodadas.
- Política de áudio: nenhuma geração de mídia nesta rodada; as propostas separam `caption` (SRT), `narration` (externa) e `postText` (publicação), conforme a regra de vídeo sem áudio.

## 1. Fluxo existente reaproveitado

- `tools/studio_planning.py`: `build_stage_prompt` (instruções canônicas da etapa), `validate_and_stage_suggestion` (importador validado pelo núcleo), histórico `suggestionHistory`, `accept_suggestion` (incorporar) e `apply_planning_to_editors` (aplicar).
- `tools/video_studio.py`: rotas `GET /api/works/planning`, `POST /api/works/planning/prompt|import|accept-suggestion|apply`, com verificações de Host/Origin nas escritas.
- `tools/studio/planning.js`: histórico com **Visualizar / Incorporar** e controles de incorporação/aplicação já existentes — **nenhuma mudança de UI foi necessária**; a prova mostrou que o fluxo completo já está disponível para propostas registradas via MCP.
- `platform/schemas/planning-suggestion.schema.json`: contrato `creative` exige `videoScenes` e `carouselCards`; validação pelo núcleo via `render_bridge.mjs --planning-suggestion`.

## 2. Implementação

- `tools/studio_mcp_server.py` (novo): servidor MCP stdio em JSON-RPC 2.0 (newline-delimited), **sem SDK** (stdlib). Adaptador HTTP isolado (`StudioHttpClient`) com destino fixo em `127.0.0.1`, porta configurável (`--port` / `STUDIO_MCP_PORT`), tempo limite por chamada e envio de Host/Origin. Handshake `initialize`, `tools/list`, `tools/call`, `ping`; diagnósticos no stderr.
  - `consultar_planejamento`: reusa `build_stage_prompt` (rota `prompt`, etapa `creative`) e expõe briefing, perfis permitidos, `contextFingerprint`, `briefingSha256` e instruções; sem conexões/chaves/caminhos.
  - `enviar_proposta`: reusa o importador (rota `import`) com `expectedContextFingerprint` obrigatório; devolve `suggestionId`, `diffPreview`, `warnings`. Erros mapeados: `INVALID_ARGUMENTS`, `CONTEXT_CONFLICT` (409, instrução de recarregar), erro útil do validador (`failureCode`), `STUDIO_UNAVAILABLE` (instrução de iniciar o Studio).
- `tools/studio_planning.py` (correção de causa): `validate_and_stage_suggestion` passou a **reconferir o `contextFingerprint` sob o `_STATE_LOCK` existente** antes de gravar, fechando a janela entre a validação (fora do lock) e o registro. Os campos `base*` do registro usam o fingerprint reconferido. Conflito preserva o estado anterior.
- `.github/workflows/local-render-validation.yml`: passo novo "Prova de entrada MCP de Planejamento (Studio HTTP, cliente MCP de teste sobre stdio)", porta 8810, Ubuntu + Windows.
- `tools/produce/README.md`: seção de uso com configuração portável por projeto no Codex (`.codex/config.toml`) e no Claude Code (`.mcp.json` / `claude mcp add -s project`), exemplos Windows/Linux e comandos reproduzíveis.

## 3. Provas executadas

### 3.1 Regressão MCP (cliente MCP de teste sobre stdio, Studio real em loopback)

Comando: `python -m unittest tools.tests.test_studio_mcp -v` → **10/10 OK** (~65 s).

Cobertura: handshake `initialize`/`tools/list`/`tools/call`; dois clientes (papéis Codex e Claude Code) no mesmo trabalho com duas propostas `creative` válidas (foco roteiro e foco carrossel) e dois IDs persistidos no histórico; editores inalterados até incorporar+aplicar (caminho completo com a proposta de roteiro); trabalho inexistente; payload inválido (`PLANNING_SELECTED_HOOK_UNKNOWN`, `carouselCards` vazio); fingerprint vencido após edição (`CONTEXT_CONFLICT`); **edição concorrente no momento da gravação** (reconferência sob lock, prova determinística) preservando estado; dois envios válidos concorrentes (dois registros); Studio indisponível (instrução de início); varredura de segredos/caminhos nas respostas MCP. Logs: `.workspace/logs/studio-mcp-planning-v1/suite-mcp-1.log` e reexecução com build fresco da platform `suite-mcp-2.log` (10/10 OK).

### 3.2 Prova de uso HTTP + stdio (CI)

Comando: `python tools/ci_studio_mcp_proof.py --port 8810` → **exit 0**.

Saída: `{"clients": 2, "proposals": 2, "rejections": {"nonexistentWork": true, "invalidPayload": true, "staleFingerprint": true, "concurrentEditAtWrite": true, "studioUnavailable": true}, "leaks": 0, "suggestionIds": ["sug-8b8e265129", "sug-fb6d0c1600"], "historyCount": 2, "editorChangedOnlyAfterApply": true, "concurrentValidSubmits": 2}`.

Exercita as rotas HTTP reais e a persistência do histórico; o servidor MCP roda como subprocesso stdio real. Logs: `.workspace/logs/studio-mcp-planning-v1/ci-mcp-proof-1.log` (diagnóstico de alias HTTP), `ci-mcp-proof-2.log` (verde) e reexecução com build fresco `ci-mcp-proof-3.log` (verde).

### 3.3 Gates afetados

Comando: `python -m unittest tools.tests.test_studio_mcp tools.tests.test_video_studio.StudioPlanningAndLLMAdapterTest -v` → **18/18 OK** (~190 s). `git diff --check` limpo. Log: `.workspace/logs/studio-mcp-planning-v1/suite-affected-1.log`.

### 3.4 Prova no navegador (Chromium real, Playwright)

Studio da branch em `127.0.0.1:8765`; trabalho fictício `browser-mcp-work` seedado com duas propostas via dois clientes MCP (`sug-6b95f8fc50` roteiro/Codex, `sug-be80ff540f` carrossel/Claude Code). Fluxo: reabrir trabalho → aba **Planejamento** → histórico mostra os **dois IDs** com **Visualizar / Incorporar** → clicar **Visualizar / Incorporar** abre "Sugestão validada (creative · import) — pronta para incorporar" → **Incorporar sugestão ao rascunho** (toast "Sugestão incorporada ao rascunho de planejamento.", rascunho atualizado) → **recarregar a página e reabrir** mantém os dois IDs e o rascunho incorporado. Capturas (4): `.workspace/logs/studio-mcp-planning-v1/browser/01-planejamento-historico-duas-propostas.png` … `04-historico-apos-recarregar.png`.

### 3.5 Suíte completa e build da platform

- A platform não foi alterada nesta rodada. O worktree recebeu inicialmente uma **cópia do `platform/dist` da main, que estava desatualizada** (sem o contrato de `framing` em `compile-video-request.js`); a 1ª execução da suíte completa (`python-suite-full-1.log`, 268 testes) falhou em 7 testes + 1 erro **alheios a esta entrega** (`test_scene_framing_preview`, `test_studio_queue`, `test_studio_templates`) com `VIDEO_REQUEST_SCENES_INVALID` / `KeyError: 'framing'` — sintoma de validador/compilador antigos, não de regressão do código novo.
- Correção de ambiente: `npm ci` + `npm run build` da platform **no worktree** com Node 22 (cache npm dentro da raiz); o `dist` fresco passa a conter `framing`. Revalidação isolada de `test_scene_framing_preview` → **4/4 OK** (145 s). Regressão MCP e prova de uso reexecutadas com o build fresco → 10/10 e exit 0.
- 2ª execução da suíte completa (registro definitivo, já com o build fresco da platform): `REQUIRE_RENDER=1 python -m unittest discover -s tools/tests -v` → **268/268 OK, 0 falhas, 0 erros, 0 skips, 2361,6 s**, exit 0. Log: `.workspace/logs/studio-mcp-planning-v1/python-suite-full-2.log`. Os 268 incluem os 10 testes MCP novos; os 258 anteriores permanecem verdes.

## 4. Clientes verificados

- **Codex e Claude Code (CLI) não estão instalados nesta estação.** As interações dos dois papéis foram provadas pelo **cliente MCP de teste sobre stdio** (`McpStdioClient`), que executa o handshake e as chamadas reais contra o servidor MCP subprocesso, com o Studio real em loopback. A configuração por projeto para ambos os clientes está documentada (seção 2 / README) e é reproduzível quando os CLIs estiverem disponíveis. Nenhum cliente real foi presumido como verificado.

## 5. Limites e pendientes

- V1: apenas consulta + registro de propostas `creative`; sem edição conversacional, sem geração de mídia, sem pesquisa de referências, sem publicação.
- A incorporação e a aplicação aos editores permanecem ações do operador no Studio.
- Publicação/PR/merge desta rodada dependem de autorização explícita do titular; a entrega inicial é branch técnica + commits + diff para revisão.