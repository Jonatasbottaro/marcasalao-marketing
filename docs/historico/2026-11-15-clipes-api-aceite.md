# Aceite — Clipes por API (texto para vídeo) no Video Studio

- Data: 2026-11-15
- Branch técnica: `codex/studio-video-api-v1` (base `main` = `3f33ea7ab64e94b8c2d1220a07debafec213bd44`, PR #14 integrada em `9c90f67`)
- Escopo: primeiro fluxo de texto para vídeo do Studio com Google Gemini Omni Flash (`gemini-omni-1.2-flash`) pela Interactions API; seleção por projeto na aba Conexões; acompanhamento sem repetição de submissão; importação silenciosa na Biblioteca; saída pela Fila de Produção. Geração de vídeo por outros provedores, entrada MCP e pesquisa de referências ficam para rodadas próprias.
- Política de áudio: o fornecedor devolve áudio nativo; o Studio importa e exporta **sem faixa de áudio** (`-an`, FFprobe com 0 faixas), com SRT e narração TXT separados. Nenhuma narração/música/efeito foi gerado.
- Aceite executado com **fornecedor simulado e credenciais sintéticas**; teste com conta real é validação operacional posterior, não realizada nesta rodada.

## 1. Referência oficial conferida

- `https://aistudio.google.com/docs/video`: Omni Flash (`gemini-omni-1.2-flash`) é o modelo de vídeo da API Gemini; Veo 3.1 Preview encerrado em 22/10/2026.
- `https://aistudio.google.com/docs/omni`: `POST /v1beta/interactions` com `model`, `input`, `response_format` (`type: "video"`, `aspect_ratio` 16:9/9:16, `resolution` 360p/720p/1080p/4k, `duration` "3s"–"15s", padrão 10 s). Resposta REST organiza o vídeo em `steps[].model_output.content[]` (`type: "video"`, `mime_type`, `data` base64 ou `uri`); `output_video` é conveniência apenas de SDK. `delivery: "uri"` retorna URI de arquivo para consulta até `ACTIVE` e download; `GET /v1beta/interactions/{id}` devolve o vídeo inline mesmo em entregas `uri`.
- `https://aistudio.google.com/docs/interactions` e `/docs/background-execution`: retenção padrão `store=true` (55 dias pago / 1 dia gratuito); `background=true` exige `store=true` e é documentado para modelos Gemini padrão e agentes gerenciados — **não documentado para o Omni Flash**, por isso não é usado nesta entrega. A confirmação ao operador informa a retenção remota antes do envio.
- Cópias das páginas consultadas: `.workspace/logs/studio-video-api-v1/api-docs/` (evidência local; não versionada).

## 2. Implementação

- `tools/studio_video_api.py` (novo): pedidos `vreq-*` registrados antes da chamada; estados `awaiting/processing/ready/imported/failed/uncertain`; confirmação explícita (`confirm: true`), reenvio apenas com `resubmit: true`; dedup de clique/recarregamento; evidência de tentativa incerta preservada; retomada pós-reinício por `GET /v1beta/interactions/{id}` quando há ID remoto confirmado, senão `uncertain (INTERRUPTED)`; entrega `uri` com polling de arquivo e download; histórico de chamadas na aba Conexões (capacidade `video`, uso/custo só quando o fornecedor informa).
- `tools/studio_connections.py`: capacidade `video` no provedor `google-gemini` (imagem + vídeo na mesma conexão), modelo por capacidade com padrão `gemini-omni-1.2-flash`, seleção/exclusão/legado preservados, `Testar` reporta se o modelo de vídeo aparece na lista oficial de metadados.
- `tools/studio_media.py`: origem `generated-google-gemini-video`; importação reutiliza `inspect_video_file`, promoção conjunta arquivo + registro e versões imutáveis.
- `tools/video_studio.py`: rotas `GET /api/works/video-requests`, `POST /api/works/video-requests/create|submit|check|import` (Host/Origin nas escritas, erros com código), `videoRequestsFile` por trabalho, retomada na inicialização e parada das consultas no `close()`.
- UI (`tools/studio/index.html`, `media.js`, `app.js`): seção **Clipes por API** na aba Mídias com **Gerar clipe** (formulário → confirmação com conexão, modelo, texto, parâmetros e avisos de retenção/cobrança/áudio), **Acompanhar** (consulta + polling local), **Importar na Biblioteca** (idempotente) e **Reenviar** explícito; seleção de vídeo por projeto na aba Conexões; histórico com uso.
- Normalização: FFprobe de duração/dimensões/contêiner/codec; MP4 H.264 quando necessário; `-an` sempre; FFprobe do produto final com 0 faixas de áudio; proveniência com fornecedor, modelo, conexão, parâmetros, `remoteInteractionId`, hash de origem e hash final.

## 3. Provas executadas

### 3.1 Testes dedicados (fornecedor simulado, cofre simulado)

Comando: `python -m unittest tools.tests.test_studio_video_api tools.tests.test_studio_connections -v`

- Resultado: **15/15 OK** (8 novos + 7 de regressão de Conexões), primeira execução.
- Cobertura: dois projetos com a mesma conexão Google (imagem + vídeo) e modelo por projeto; confirmação com avisos; importação silenciosa idempotente com proveniência e FFprobe; falhas (credencial recusada, limite, resultado inválido, sem vídeo); resposta incerta após envio com reenvio explícito; clique duplicado sem nova submissão; reinício com retomada por ID remoto e marcação `INTERRUPTED` sem ID; entrega `uri` com polling; conexão por variável de ambiente resolvida na chamada; ausência de conexão (`VIDEO_CONNECTION_REQUIRED`); varredura de segredos em estado/respostas/arquivos; `Testar` reportando o modelo de vídeo listado.
- Log: `.workspace/logs/studio-video-api-v1/suite-video-conn-1.log`.

### 3.2 Prova HTTP completa (CI)

Comando: `python tools/ci_studio_video_api_proof.py --port 8808`

- Resultado: **exit 0** — `{"videoPosts": 8, "imageCalls": 1, "videoCalls": 8, "queueCompleted": 1, "deliveryAudioStreams": 0, "resumedAfterRestart": 1}`.
- Cobre: dois projetos fictícios; mesma chave Google para imagem e vídeo; modelo por capacidade; confirmação com retenção/cobrança; falhas e reenvio explícito; reinício com geração iniciada e retomada; importação repetida = mesma versão; clipe selecionado em cena; **Fila de Produção concluída** com entrega final FFprobe **0 faixas de áudio** + SRT + TXT não vazios; varredura de segredos em respostas, `connections.json` e arquivos dos trabalhos; chave sintética apenas nas chamadas autenticadas esperadas do simulador.
- Logs: `.workspace/logs/studio-video-api-v1/ci-video-proof-*.log` (execuções 1–3 diagnosticaram caminho longo do Windows na limpeza/varredura e o formato do índice de entrega; corrigidos na própria prova; execução final verde).
- Passo novo no CI: `.github/workflows/local-render-validation.yml` — "Prova de clipes por API texto para video (Studio HTTP, Interactions API simulada)", porta 8808, Ubuntu + Windows.

### 3.3 Suítes afetadas e suíte completa

- Afetadas (Conexões, enquadramento, fila, clipes por API): `python -m unittest tools.tests.test_studio_video_api tools.tests.test_studio_connections tools.tests.test_scene_framing_preview tools.tests.test_studio_queue -v` → **25/25 testes reais OK** (442,6 s). Um erro adicional de loader foi causado por nome de módulo inexistente digitado no comando (`test_media_library`; o correto, `test_studio_media`, está na suíte completa). Log: `.workspace/logs/studio-video-api-v1/suite-affected-1.log`.
- Suíte completa, 1ª execução: `REQUIRE_RENDER=1 python -m unittest discover -s tools/tests -v` → 258 testes, 1 erro: `test_queue_process_restart.test_02` (promoção órfã) excedeu o timeout de 360 s sob carga com a tentativa ainda `running` (pid vivo) — mesmo transiente de Windows observado na rodada de Conexões, sem relação com o código novo. Log: `.workspace/logs/studio-video-api-v1/python-suite-full-1.log`.
- Revalidação isolada do teste afetado: `REQUIRE_RENDER=1 python -m unittest tools.tests.test_queue_process_restart -v` → **2/2 OK em 55,1 s**. Log: `.workspace/logs/studio-video-api-v1/suite-restart-isolated-2.log`.
- Suíte completa, 2ª execução: 258 testes, 1 erro distinto: `test_produce_video.test_completed_then_failed_preserves_last_valid` — `PermissionError [WinError 5]` no `os.replace` de `produce_video._write_index_atomic` (código existente; destino temporariamente preso por outro processo no Windows sob carga). Log: `.workspace/logs/studio-video-api-v1/python-suite-full-2.log`.
- Correção no escopo: retry curto (6 tentativas, backoff 0,2–1,2 s) apenas para `PermissionError` no replace do índice, mesmo padrão já aceito em `studio_templates._replace_dir_with_retry` (commit `4d8e8f8`).
- Revalidação isolada dos dois módulos afetados: `REQUIRE_RENDER=1 python -m unittest tools.tests.test_produce_video tools.tests.test_queue_process_restart -v` → **20/20 OK em 259,4 s**. Log: `.workspace/logs/studio-video-api-v1/suite-produce-restart-isolated.log`.
- Suíte completa, 3ª execução (registro definitivo): `REQUIRE_RENDER=1 python -m unittest discover -s tools/tests -v` → **258/258 OK, 0 falhas, 0 skips, 2312,3 s**, já com o retry do índice (`4d8e8f8`). Log: `.workspace/logs/studio-video-api-v1/python-suite-full-3.log`.

### 3.4 Prova no navegador (Chromium real, Playwright)

- Servidor local com Interactions API simulada (porta 8811) e Studio da branch (porta 8765), cofre simulado, projeto/trabalho/conexão seedeados (`google-browser`, chave sintética `e2e-video-key-1`).
- Fluxo percorrido pela UI: aba Conexões (capacidades `image, video`; seleção de vídeo e imagem do projeto) → trabalho `browser-vapi-work` → Mídias → **Gerar clipe** (5 s, 9:16, 720p) → confirmação com conexão/modelo/texto/avisos → **recarregamento da página recuperou o mesmo pedido** `vreq-eb5efbb48b` em "Aguardando confirmação" → **Confirmar envio** → "Em processamento" com **Acompanhar** → "Pronto para importar" → **Importar na Biblioteca** → mídia `clipe-api-vreq-eb5efbb48b`, versão `v-0e35f0f606`, ID remoto `v1_browser_1` → histórico de Conexões com chamada `video` completed e uso `prompt 12 · resposta 34 · total 46`.
- Evidência backend: 1 única chamada autenticada ao simulador com a chave esperada e `response_format` correto; versão importada `video/h264`, origem `generated-google-gemini-video`, `audioRemoved: true`; FFprobe do arquivo importado com **0 faixas de áudio**; chave sintética ausente de overviews e de todos os arquivos do trabalho.
- Capturas (5): `.workspace/logs/studio-video-api-v1/browser/01-conexoes-selecao-video.png` … `05-historico-video.png`; resumo em `.workspace/logs/studio-video-api-v1/browser-evidence.md`.
- Correção de UI encontrada na prova: `append` nativo com filhos condicionais `null` renderizava o texto "null" nos cards/diálogo; corrigido com `filter(Boolean)` em `media.js` e revalidado no navegador.

## 4. Gates da platform

O núcleo `platform/` não foi alterado nesta rodada (contratos e API pública inalterados). Typecheck/build e suíte da platform executados como regressão: ver logs em `.workspace/logs/studio-video-api-v1/`.

## 5. Integração

- Autorização do titular em 15/11/2026: "Publicar + PR + merge".
- Branch `codex/studio-video-api-v1` publicada; [PR #15](https://github.com/Jonatasbottaro/marcasalao-marketing/pull/15) mergeada pelo merge commit `17179665b55496b3d4531d855c876c2951441f7f`, com os cinco commits originais preservados (`c45e502`, `019f68c`, `a69a0a0`, `4d8e8f8`, `bf2ed3f`).
- CI do PR verde em Ubuntu + Windows: runs `43767371717` (push) e `43767403098` (PR). CI pós-merge na main: run `43770466169`.

## 6. Limites e pendientes

- V1: apenas texto para vídeo com Google Gemini Omni Flash; um clipe por pedido; sem edição/extensão conversacional, sem imagens de referência, sem outros provedores.
- `background=true` não é usado (não documentado para o Omni Flash); a execução assíncrona é do Studio (thread em segundo plano), com consulta retomável pelo ID remoto.
- Teste com conta real Google não foi executado (validação operacional posterior).
- Entrada MCP, pesquisa de referências e demais provedores ficam para rodadas próprias; aprovação editorial e publicação seguem o fluxo vigente.