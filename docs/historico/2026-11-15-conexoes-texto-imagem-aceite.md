# Registro de aceite — Conexões de texto e imagem no Video Studio (2026-11-15)

## Escopo entregue

- **Branch técnica**: `codex/studio-connections-v1` (sobre `main` em `0f77c49a497206160689143bf8a6ec3e8221df83`, PR #13 integrada em `3f4600b`); **integrada na main pelo merge `9c90f67` (PR #14)** em 2026-11-15, por autorização explícita do titular após o aceite local.
- **Núcleo (`tools/studio_connections.py`)**: armazenamento versionado `.workspace/studio/connections.json` (conexões, seleções por projeto, histórico limitado a 200 chamadas) com gravação atômica; interface de cofre com backend Windows (CredWriteW/CredReadW/CredDeleteW, alvo `MarcaSalaoStudio/<ref>`), backend simulado para testes e resolução por variável de ambiente no momento da chamada; conexão sem chave para servidor local aberto.
- **Integração**: `llm_adapter.TextModelAdapter` aceita `apiKey` opcional (Authorization Bearer) e devolve `usage`; `image_adapters.GeminiImageAdapter` aceita config injetada e devolve `usageMetadata`/providerInfo; `studio_planning.generate_with_local_model` e `studio_media.generate_candidate` resolvem a seleção do projeto (conexão prevalece sobre `llmConfig` do painel), registram chamadas e identificam a conexão nas falhas; overviews de Planejamento e Mídia expõem a seleção sem segredo; `save_llm_config` nunca grava chave no arquivo legado.
- **Rotas**: `GET /api/connections`, `POST /api/connections/save|credential|delete|select|test`, com Host/Origin nas escritas e erros estruturados sem segredos.
- **UI**: aba **Conexões** (lista com estado da credencial e último teste, cadastro/edição, Testar, Trocar chave mantendo ID e seleções, exclusão que devolve seleções ao legado, seleção por projeto com modelo opcional, histórico com uso/custo); nota de conexão prevalente no painel do Planejamento e badge de conexão na Biblioteca de Mídia.
- **Diagnósticos**: texto local `GET {base}/v1/models`; Gemini `GET {endpoint}/v1beta/models` (metadados oficiais) com `x-goog-api-key`; códigos `OK`, `CREDENTIAL_REFUSED`, `CREDENTIAL_MISSING`, `MODEL_INCOMPATIBLE`, `RATE_LIMIT`, `UNAVAILABLE`, `TIMEOUT`; mensagens normalizadas/redigidas; Testar nunca gera conteúdo.

## Evidências executadas

Estação Windows (Node 22.23.2 WinGet, Python 3.14), worktree `<RAIZ>/.workspace/worktrees/studio-connections-v1`. Logs em `<RAIZ>/.workspace/logs/studio-connections-v1/`.

### Suítes e gates

- `tools/tests/test_studio_connections.py`: **7/7 OK** (cofre simulado + servidores HTTP simulados; dois projetos com seleções distintas de texto e imagem; troca de chave com reinício; diagnósticos 401/429/modelo fora da lista/rede/sem chave; legado por ambiente; env resolvida a cada chamada; varredura de segredos em estado/histórico/arquivos do trabalho).
- Suíte Python completa com `REQUIRE_RENDER=1`: **250/250 OK** na 3ª corrida (detalhes e diagnóstico das duas falhas transientes de Windows na seção "Suíte completa e CI" abaixo).
- Platform: `build`/`typecheck` OK; `npm test` **994/994**; `test:contracts` **324/324** (sem mudanças em `platform/` nesta rodada).
- Prova HTTP `python tools/ci_studio_connections_proof.py --port 8807`: exit 0 — seleções por projeto conferidas nos mocks (modelo/auth de texto e chave de imagem por projeto), diagnósticos, troca de chave + reinício do servidor, legado sem seleção, 14 chamadas no histórico, nenhum segredo em metadados/estado/arquivos.

### Aceite em Chromium real (Playwright, `http://127.0.0.1:8808`, cofre simulado)

Capturas em `.workspace/logs/studio-connections-v1/browser/` (01-aba-conexoes, 02-historico):

1. Dois trabalhos fictícios em projetos distintos (`e2e-conn-a`, `e2e-conn-b`).
2. Cadastro pela UI de três conexões: texto local **sem chave**, Gemini **cofre** (chave sintética gravada no backend simulado) e Gemini **variável de ambiente** (`E2E_GEMINI_KEY`, pendente até o reinício com a variável definida).
3. **Testar** pela UI: `OK` no texto local; `MODEL_INCOMPATIBLE` quando o mock listava modelos incompatíveis (diagnóstico correto) e `OK` após corrigir a lista do mock; conexão env sem variável mostra `pendente`.
4. Seleção por projeto pela UI (texto com override de modelo `other:1b` no projeto B; imagem cofre no A e env no B); geração de texto pelo botão do Planejamento usou a conexão do projeto (nota de prevalência visível; resposta validada de `qwen3:8b`).
5. Geração de imagem confirmada por projeto: mock recebeu `e2e-synthetic-key-1` (A), depois `e2e-env-key` (B, pós-reinício) e `e2e-synthetic-key-2` (A, após **Trocar chave** pela UI mantendo ID e seleções).
6. Reinício do Studio com `E2E_GEMINI_KEY` definida: conexão env passa a `configurada`, seleções preservadas, novas gerações completadas; histórico exibe projeto/conexão/capacidade/modelo/resultado e uso (tokens/imagem), custo/cota/saldo só quando informados.
7. Varredura: nenhuma chave sintética em `GET /api/connections`, `connections.json` ou arquivos dos trabalhos.

### Suíte completa e CI

- 1ª corrida completa (`python-suite-full.log`): 250 testes, 1 erro — `test_queue_process_restart.test_02` timeout esperando promoção órfã sob carga; módulo reexecutado isolado 2/2 OK. Correção de robustez no teste (`a00d6c9`): timeout reporta estado do item/tentativas, falha cedo com stdout/stderr do staging se o órfão morre sem promover, janela de 360 s.
- 2ª corrida completa (`python-suite-full-2.log`): 250 testes, 1 erro — `test_studio_templates.test_01` `PermissionError WinError 5` no `os.replace` de promoção da revisão (lock transiente do Windows em diretório recém-criado); módulos reexecutados isolados 8/8 OK. Correção (`6a1aaf1`): retry curto com backoff na promoção de diretórios (`_replace_dir_with_retry`).
- 3ª corrida completa (`python-suite-full-3.log`): **250/250 testes OK**, zero falhas, zero erros, zero skips, em `2298.547s` com `REQUIRE_RENDER=1` (inclui `test_studio_connections.py` 7/7, `test_studio_queue.py` 6/6, `test_queue_process_restart.py` 2/2 e `test_studio_templates.py` 6/6).
- Platform: `build`/`typecheck` OK; `npm test` **994/994**; `test:contracts` **324/324** (sem mudanças em `platform/`).
- Prova HTTP `ci_studio_connections_proof.py --port 8807`: exit 0 (detalhes acima).
- CI: PR #14 run [43742679544](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43742679544) no SHA `4cb8a77` — `ubuntu-latest · render real` e `windows-latest · render real` **success**, incluindo a etapa `Prova de conexoes de texto e imagem (Studio HTTP, cofre simulado)`; CI pós-merge run [43746174533](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43746174533) no merge `9c90f67` — **success** em `ubuntu-latest · render real` e `windows-latest · render real`.