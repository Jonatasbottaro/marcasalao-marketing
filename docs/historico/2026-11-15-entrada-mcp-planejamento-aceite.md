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

- **Codex e Claude Code (CLI) não estavam instalados nesta estação na data desta rodada.** As interações dos dois papéis foram provadas pelo **cliente MCP de teste sobre stdio** (`McpStdioClient`), que executa o handshake e as chamadas reais contra o servidor MCP subprocesso, com o Studio real em loopback. A configuração por projeto para ambos os clientes está documentada (seção 2 / README) e é reproduzível quando os CLIs estiverem disponíveis. Nenhum cliente real foi presumido como verificado.
- **Atualização em 16/11/2026:** o **Codex CLI oficial 0.169.0** foi executado de fato nesta estação (login ChatGPT, modelo `gpt-6.1-sol`), com `--ignore-user-config` e o servidor MCP carregado por `-c`. Ver seção 8.

## 5. Limites e pendientes

- V1: apenas consulta + registro de propostas `creative`; sem edição conversacional, sem geração de mídia, sem pesquisa de referências, sem publicação.
- A incorporação e a aplicação aos editores permanecem ações do operador no Studio.
- Publicação da branch e abertura da PR autorizadas pelo titular em 16/11/2026 (prompt "Revisão e abertura da PR do MCP"); a integração na `main` permaneceu etapa posterior e **foi executada em 16/11/2026** (seção 8).

## 6. PR e checks (16/11/2026)

- Branch publicada `codex/studio-mcp-planning-v1`; [PR #17](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/17) aberta para `main`, HEAD verificado `52ee9c0d4b11dab0467b3e2d6d53cbbbff38c5c9` (base `516a59d`, implementação `a7409e4`, aceite `52ee9c0`).
- Revisão do diff conferida: transporte stdio newline-delimited com stdout só MCP; negociação de versão ecoa a versão suportada do cliente; duas ferramentas declaradas com schemas; reconferência do `contextFingerprint` sob o lock; teste de dois clientes comprova histórico + controle do operador na aplicação. `git diff --check` limpo; escopo restrito a `tools/`, workflow e docs.
- Build da platform gerado no próprio checkout de teste (Node 22) antes das reexecuções; o workflow compila a platform (`npm ci` + `npm run build`) antes da prova MCP. Regressão MCP e prova reexecutadas no HEAD verificado: 10/10 e exit 0 (`.workspace/logs/studio-mcp-pr/suite-mcp-head.log`, `ci-mcp-proof-head.log`).
- CI da PR verde em Ubuntu + Windows: run PR [43801496589](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43801496589) e run push [43801446279](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43801446279), ambos `success` nos dois jobs, com o passo "Prova de entrada MCP de Planejamento" `success` em ambos os sistemas.
- Clientes executados: cliente MCP de teste sobre stdio (papéis Codex e Claude Code). Codex/Claude Code CLI oficiais ausentes na estação; não executados; configuração documentada no README do Studio.

## 7. Correções da revisão da PR #17 (16/11/2026)

Quatro casos apontados na revisão do checkpoint `14c4bfb6cd672e33614d9a3091709196b5e40a1c`, corrigidos na mesma branch:

1. **UTF-8 no transporte**: `serve()` passou a envolver stdin/stdout em `io.TextIOWrapper(..., encoding='utf-8')` sobre os buffers, nos dois sentidos, independente do encoding padrão (CP1252 em Windows); stderr reconfigurado para UTF-8. Teste com subprocesso `PYTHONIOENCODING=cp1252`, cliente lendo/escrevendo bytes UTF-8 e proposta com acentos ("Ação e narração — coração da agenda"): texto recebido pelo cliente (`briefing.coreMessage`) e conteúdo gravado no histórico (`videoScenes[0].caption/narration`) conferidos iguais.
2. **Prévia vinculada ao contexto validado**: `validate_and_stage_suggestion` compara sob o lock o contexto atual com o snapshot usado para validar/calcular `diffPreview`, **inclusive sem `expectedContextFingerprint`**; conflito preserva edição e histórico. Coberto: import sem fingerprint em contexto estável (base = fingerprint atual, prévia com cenas novas); import sem fingerprint com edição concorrente (409, histórico e edição preservados); dois imports válidos concorrentes sem fingerprint (dois registros). O conflito por fingerprint enviado desatualizado foi preservado.
3. **Etapa no envio MCP**: `enviar_proposta` passa `stage: "creative"` ao importador. Proposta `briefing` válida em seu contrato enviada pelo MCP → `PLANNING_STAGE_MISMATCH`, histórico preservado; import de briefing pelo Studio (`stage: "briefing"`) continua 200.
4. **Versões negociadas**: removida `2025-03-26` (exige lotes JSON-RPC) da lista suportada; oferecidas `2025-06-18` e `2024-11-05` (sem lotes), documentadas no servidor e no README. Lote de `ping` → `Invalid Request` (-32600). Handshake testado para as versões anunciadas (eco) e para versões fora da lista (`2025-03-26`, `1999-01-01` → `2025-06-18`).

Provas observadas após as correções (build fresco da platform no checkout de teste, Node 22):
- Regressão MCP `tools.tests.test_studio_mcp`: **16/16 OK** (~99 s), incluindo os novos testes 11–16.
- Regressão Planejamento `test_video_studio.StudioPlanningAndLLMAdapterTest`: **8/8 OK** (~128 s).
- Prova `tools/ci_studio_mcp_proof.py --port 8810`: **exit 0**, com `utf8UnderCp1252: true`, `studioBriefingImportOk: true`, `versionNegotiation: true`, `batchRejected: true`, `rejections.mcpBriefingStage: true`, além dos marcadores anteriores (2 clientes, 2 propostas, concorrência, 0 vazamentos, editores só após aplicar).
- `git diff --check` limpo. Logs em `.workspace/logs/studio-mcp-fix/`.
- Clientes: apenas o cliente MCP de teste sobre stdio (Codex/Claude Code oficiais seguem ausentes); nenhum teste oficial executado nesta rodada.

## 8. Aceite em cliente oficial, merge de teste e integração (16/11/2026)

### 8.1 Aceite no Codex CLI oficial (PR #17, `1cc1ecd`)

Cliente: **Codex CLI 0.169.0** instalado localmente em `.workspace/tools/codex-mcp-aceite`
(`@openai/codex@latest`), login ChatGPT, modelo padrão da conta `gpt-6.1-sol`.
A CLI global 0.114.0 não executou o turno: não oferecia `--ignore-user-config` e falhava ao
carregar `~/.codex/config.toml` (`unknown variant "default"` em `service_tier`). A instalação
local resolveu os dois pontos **sem alterar a configuração global**.

- Turno mínimo: `codex exec --ignore-user-config "Responda apenas OK."` → `OK`
  (sessão `01a1e4ca-8611-7a30-88b5-9dda4502658b`).
- Turno MCP: `codex exec --ignore-user-config --approve-for-me --json` com
  `-c mcp_servers.video-studio-planejamento.command='python'` e
  `-c ...args=['tools/studio_mcp_server.py','--port','8811']`.
- Ferramentas descobertas: `consultar_planejamento`, `enviar_proposta`.
- Handshake: `protocolVersion = 2025-06-18`, `serverInfo = video-studio-planejamento 1.0.0`.
- Trabalho fictício `aceite-mcp-cliente-oficial` com briefing "Ação de divulgação da agenda"
  (`contextFingerprint = 244a3e45…c082a`).
- Proposta `creative` registrada pelo cliente oficial: **`sug-b5a65d9a90`**
  (`createdAt 2026-11-16T14:45:29Z`), com `videoScenes`, `carouselCards` e `channelCopies`;
  `lastApplied = null`, rascunhos de vídeo (2 cenas) e carrossel (3 cards) intactos.
- Evidências: `.workspace/logs/studio-mcp-cliente-oficial/`.

### 8.2 Merge de teste com a `main` atual

Base do teste: `origin/main` = `b4f886971a9d996a1cd0e3bcf93cddfc143420f3` (PR #18, piloto Astryx),
enquanto o CI anterior da PR #17 havia rodado sobre a main antiga `516a59d`.

- Merge local (`git merge --no-commit --no-ff origin/main`) **sem conflitos**, com mesclagem
  automática apenas em `tools/produce/README.md`.
- `npm ci --prefix platform` e `npm run build --prefix platform` sem erros.
- `python -m unittest tools.tests.test_studio_mcp -v` → **16/16 OK**.
- Prova MCP no resultado do merge, no Codex CLI 0.169.0, trabalho `aceite-mcp-integracao`
  (`contextFingerprint = 562785bd…47046`): **`suggestionId = sug-4205f0002f`**
  (`createdAt 2026-11-16T15:07:46Z`), histórico com 1 registro, editores preservados
  (`cena-1`/`cena-2` e `capa`/`conteudo`/`fechamento`), `lastApplied = null`.
- Evidências: `.workspace/logs/studio-mcp-integracao/`.

### 8.3 Integração e CI da `main`

- Merge de integração `4976c2365900237c12ba013cb0ccb93eac4aeb95`
  ("Merge pull request #17 from Jonatasbottaro/codex/studio-mcp-planning-v1"), enviado a `main`.
- PR #17 **fechada como integrada** (`merged = true`, `merge_commit_sha = 4976c23`).
- CI da `main` verde: run
  [43906457080](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43906457080)
  (`push`), `success` em **ubuntu-latest** e **windows-latest**, com os 31 passos
  concluídos — incluindo "Suite Python com render obrigatório" e
  "Prova de entrada MCP de Planejamento (Studio HTTP, cliente MCP de teste sobre stdio)".