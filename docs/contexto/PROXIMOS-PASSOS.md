# Próximos passos

Antes de escolher uma tarefa, reconfira [ESTADO-ATUAL.md](ESTADO-ATUAL.md), a main remota e as PRs. A lista abaixo organiza trabalho possível; não autoriza produção, publicação ou a execução automática de todas as etapas.

A **regra permanente de armazenamento** em [AGENTS.md](../../AGENTS.md) é normativa para toda tarefa: a raiz oficial é o próprio checkout principal (`<RAIZ>` = `git rev-parse --show-toplevel`, qualquer que seja o caminho nesta estação), artefatos auxiliares somente em `.workspace/` por categoria e tarefa, validação de contenção antes de criar arquivo, limpeza ao final e handoff com confirmação textual. A orientação de segurança de worktrees (conferir sessão ativa, `git worktree move`/`remove`, nunca `rm -rf` em worktree registrada, autorização do titular para mover ou remover) faz parte dessa regra.

**O invariante são os arquivos, não o caminho.** O projeto está em mais de um computador e pode ser aberto por IDEs diferentes, cada um com sua pasta local. O que precisa estar idêntico e atualizado em todas as estações são os arquivos versionados, alinhados por Git: atualizar com `fetch`/`pull --ff-only` antes de trabalhar, commitar e enviar o que for permanente ao terminar, nunca alinhar por cópia manual de pastas ou sincronizador de nuvem, e não padronizar caminhos entre máquinas. `.workspace/` é local e não sincroniza — evidência que precise existir em outra estação deve ser versionada. Se um documento recebido afirmar uma raiz que não existe nesta estação ou proibir o diretório onde o checkout está, interromper e pedir decisão ao titular; não realocar por conta própria.

Para as próximas rodadas, o titular prefere agrupar código, integração, testes e documentação de um mesmo resultado em um prompt de entrega. Inclua os pontos de verificação dentro da execução e preserve o escopo de autorização de cada etapa.

## 1. Deliberar sobre a próxima fatia de TEMPORAL-02

> Manter o projeto bloqueado ou autorizar uma próxima fatia específica de TEMPORAL-02, com escopo delimitado pelo titular. A ratificação da fatia Workflow foi registrada em 11/11/2026 e não autoriza nenhuma fatia posterior.

A main conferida em 11/11/2026 está em `2c409676e58e4e118d865821b9a0cbdd93a22364`. O último commit técnico do núcleo é `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`, com R001 e BeatPlan v1 integrados. Os seis commits posteriores atualizam documentação e governança. A limpeza de 14 branches remotas autorizada pelo titular ficou registrada em `3c44ae4`. A PR #1 (`codex/ai-memory-integration`) é a única aberta na leitura. Em 12/11/2026 o piloto técnico local R002 (vídeo sem áudio, fora do núcleo) foi integrado pelo merge `b7ed1d9bbf397f5e9f14bfddc62c67aa0d4f5cf9` com o corretivo `0ac4bde8e5096ecdf4913a48ad453e066346b213`; não altera `platform/`, `orchestration/` nem os bloqueios abaixo. Também em 12/11/2026 a **execução local de TEMPORAL-02** (cliente, Worker local, CLIs, replay formal e gate Elephant–Goldfish, em `orchestration/temporal/`) foi integrada pelo merge `5376890974d4baf49b341297a9b7b0071a680dc6` a partir de `codex/temporal-02-execucao-local` (`63d04d5`), por pedido explícito do titular; escopo estritamente local, sem alterar os bloqueios de produção abaixo. Ainda em 12/11/2026, o **segundo consumidor real (Multitrack Hub) e os casos de pipeline** foram integrados pelo fast-forward `f8ad1ea..36551ded3e34520a4e7da3c07ee413b19020956b` a partir de `codex/multitrack-pipeline-consumer`, por autorização explícita do titular em entrega multiprojeto; escopo estritamente interno à `platform`, sem alterar os bloqueios abaixo. Na mesma data, o **CreativeExecutionPackage v1** (pacote técnico de execução derivado do pipeline válido, com CLI transacional `content:build-execution-packages`) foi integrado pelo merge commit `dbf4d31c9f0882827f9fdf9bb79f18f00b3d092d` a partir de `codex/creative-execution-package-v1`, por autorização explícita do titular; o pacote não executa nada e não altera os bloqueios abaixo. Ainda em 12/11/2026, o **executor local simulado v1** (consome o pacote e produz somente plano, eventos, relatório, artefatos textuais simulados e hashes, com CLI `content:simulate-execution`) foi integrado pelo merge commit `2824728300f20c89fe02717e29130895996ae85b` a partir de `codex/simulated-execution-runner-v1`, por autorização explícita do titular; o adaptador `simulation` não é renderer, não produz mídia e não altera os bloqueios abaixo. Na sequência, o **primeiro adaptador de render local de prova** foi integrado pelo merge commit `5be61b8cb3c1894088aae950a81469633447c45f` (com workflow de render real em CI nos dois sistemas operacionais), e o **pipeline local de renderização a partir de casos** (`tools/render_pipeline.py`) foi implementado e integrado com prévia (`--plan-only`), render e2e com pacote canônico gerado em memória, promoção atômica com manifesto de entrega versionado (`delivery-manifest.json`), 18 testes dedicados e CI de render real atualizado.

- **TEMPORAL-02-01**: fronteira pública mínima da `platform`, integrada em `f202377fac721aff1d4143a2598f76c03062f0ac`;
- **TEMPORAL-02-02**: `CompositionValidationWorkflowInput` e preflight local, integrados em `29b40783320360350e59a13e39f49a60d2308507`;
- **TEMPORAL-02-03**: Activity real [`validateCompositionActivity`](../../orchestration/temporal/src/activities/composition-validation-activity.ts), integrada em `db84270ad3e51eecb0b562fcdf3a7e36941288ab`, com ratificação estrita registrada em `8f94e0205b470b46da918d78f8136fafa9a2286a`;
- **Fatia Workflow**: [`validateCompositionWorkflow`](../../orchestration/temporal/src/workflows/composition-validation-workflow.ts), [`CompositionValidationWorkflowResult`](../../orchestration/temporal/src/workflows/composition-validation-result.ts), [classificador de falhas](../../orchestration/temporal/src/workflows/composition-validation-failure-classifier.ts) e Retry Policy canônica do PRD integrados e homologados tecnicamente em `f5842107a0f307b4cc208c15fc4509c6d7d31f72`, com ratificação do titular registrada em 11/11/2026;
- **BeatPlan v1 interno**: [`beat-plan-contract.ts`](../../platform/src/beat-plan-contract.ts), [`beat-plan.schema.json`](../../platform/schemas/beat-plan.schema.json), `BeatPlanValidationReport` em [`validation-report.ts`](../../platform/src/validation-report.ts), [`validate-beat-plan.ts`](../../platform/src/validate-beat-plan.ts), [`validate-beat-plan-cli.ts`](../../platform/src/validate-beat-plan-cli.ts) e [dois exemplos](../../platform/examples/beat-plans/), reconciliados em `7d919fc208ac4dfeebe5b0b65a959171e5f093f2` e integrados pelo merge `d5761b1f37d1a5b5e55e2f1b7422c969e6194957`. Integração **técnica e interna**: não amplia a API pública, não se combina com OutputPlan e não entra no Temporal.

A evidência da fatia Workflow é de **17 testes novos, 162 testes aprovados, zero falhas, zero ignorados e repetibilidade 7/7**, exclusivamente em `f584210`. O CI da [branch técnica, run 42950735743](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42950735743), e da [main nesse SHA, run 42953193438](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/42953193438), está verde em Ubuntu e Windows, Node 22. Não são testes dos HEADs posteriores `e86f3c9`, `d5761b1`, `c50dc86`, `9908f3b` e `79fd5da` nem foram repetidos nesta atualização documental. As evidências anteriores de cada fatia e os limites estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md) e no [README do Temporal](../../orchestration/temporal/README.md).

A evidência do BeatPlan v1 é de **626 testes aprovados, zero falhas e zero skips** na matriz de quatro ambientes — Ubuntu Node 22, Ubuntu Node 24, Windows Node 22 e Windows Node 24 —, com CI da [branch reconciliada, run 43034990448](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43034990448), em `7d919fc`, e da [main, run 43099977731](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43099977731), em `d5761b1`. Esses números pertencem a esses commits e não devem ser atribuídos a um commit documental posterior. O detalhe por componente, as regras e as fronteiras estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md) e no [README da platform](../../platform/README.md).

A fatia Workflow de TEMPORAL-02 está tecnicamente integrada e homologada no commit `f584210` e **ratificada pelo titular em 11/11/2026**. A ratificação abrange exclusivamente `validateCompositionWorkflow`, `CompositionValidationWorkflowResult`, `classifyCompositionActivityFailure`, a chamada tipada de `validateCompositionActivity`, os resultados `valid`, `invalid` e `failed`, a Retry Policy canônica do PRD, a classificação sanitizada de falhas, os testes puros, os testes de fronteira e os testes com `TestWorkflowEnvironment`, o Worker efêmero usado exclusivamente nos testes e o CI verde em Ubuntu e Windows, Node 22.

A ratificação não aprova o PRD completo e não autoriza nova implementação. Nada fora dessa lista foi ratificado: cliente Temporal de validação, Worker de produção, `workflow.start` da aplicação, Workflow ID e suas políticas, colisão, `contentHash`, replay formal e o gate Elephant–Goldfish seguem bloqueados, como abaixo.

O [PRD de TEMPORAL-02](../planejamento/TEMPORAL-02-validacao-de-composition.md) permanece formalmente em revisão, sem aprovação global. TEMPORAL-02 não está concluído integralmente, e nenhuma implementação posterior foi autorizada. Não reimplementar o Workflow já integrado nem definir antecipadamente qual será a próxima fatia.

Continuam estritamente bloqueados até autorização específica:

- Worker de produção dedicado à composição;
- cliente Temporal de validação;
- `workflow.start` da aplicação;
- Workflow ID de composição;
- `WorkflowIdReusePolicy` e `WorkflowIdConflictPolicy` de composição;
- colisão de Workflow ID;
- replay formal;
- gate Elephant–Goldfish de TEMPORAL-02;
- integração final completa de TEMPORAL-02;
- combinação BeatPlan × OutputPlan;
- combinação de OutputPlan e outros planos no Temporal;
- renderização de campanha real e adaptadores de fornecedores externos;
- `VisualAnchor`, `AudioPlan` e `RenderPlan`; (`VisualStyle` v1 e `AssetManifest` v1 integrados apenas no pipeline local e contratos internos da `platform`);
- mídia;
- fornecedores;
- TEMPORAL-04;
- deploy.

Worker efêmero, cliente, `workflow.start` e IDs usados nos testes desta fatia não são implementação desses componentes na aplicação. Replay formal não foi executado nem aprovado, e o gate Elephant–Goldfish de TEMPORAL-01 não vale como aprovação de TEMPORAL-02. `contentHash` continua fora de TEMPORAL-02.

As pré-condições técnicas já cumpridas — fronteira pública, input/preflight, Activity ratificada, Workflow ratificado em escopo estrito, Retry Policy exercitada e núcleo sem dependência Temporal — não substituem a decisão de governança. A ratificação da fatia Workflow não abre autorização automática: qualquer próxima implementação exige decisão separada do titular, com escopo explícito.

## 2. Validação consolidada do pipeline criativo e combinação no Temporal

> A validação consolidada local do pipeline criativo foi autorizada, implementada e integrada na main pelo merge `c461a3ca11e51ffe7082f7b11661632c0024def0` em 12/11/2026. A combinação permanece estritamente local e interna à `platform`, sem integrar ao Temporal.

A combinação LOCAL e determinística entre os contratos foi concluída com sucesso:

- `validateContentPipeline(input)` unifica em uma única execução `ProjectManifest` → `Composition` → `OutputPlan` → compatibilidade `Composition × OutputPlan` → `BeatPlan`;
- Contrato estruturado `ContentPipelineValidationReport` com discriminative union `ContentPipelineStageResult`, DAG de dependências estrito e tratamento aditivo de warnings;
- CLI interna `content:validate-pipeline` com flags `--project`, `--composition`, `--output-plan`, `--beat-plan` e `--json`;
- Fixtures integradas em `platform/examples/pipelines/`;
- 651 testes na platform com CI verde em Ubuntu e Windows × Node 22 e 24.

O que permanece bloqueado e requer deliberação explícita do titular:

- Uso dessa combinação ou de qualquer outro agregador dentro do Temporal;
- Criação de Workflow, Activity ou Worker Temporal para o pipeline consolidado;
- TEMPORAL-04;
- Renderização, adaptadores, geração de vídeo, imagem ou áudio;
- Mídia, fornecedores e deploy.

## 3. Provar o segundo consumidor real — concluído em 12/11/2026

> A prova do segundo consumidor real foi autorizada, implementada e integrada na main pelo fast-forward `f8ad1ea..36551ded3e34520a4e7da3c07ee413b19020956b` em 12/11/2026, a partir da branch `codex/multitrack-pipeline-consumer`. Detalhe e evidências em [ESTADO-ATUAL.md](ESTADO-ATUAL.md), seção Segundo consumidor real — Multitrack Hub e casos de pipeline.

Critérios de conclusão atendidos:

- o mesmo núcleo valida os dois consumidores (Marca Salão e Multitrack Hub) sem condicionais de marca — a varredura de independência de marca do núcleo foi estendida e proíbe também referências à Multitrack Hub em `platform/src` e `platform/schemas`;
- tema, domínio, assets, CTA e políticas são dados do projeto: as fixtures da Multitrack Hub declaram `brandTheme`, `assetRoot`, allowlist e políticas próprios, e o núcleo apenas os valida;
- as configurações não inventam funcionalidades nem importam autorizações de outra marca: as fixtures são técnicas e fictícias, não reutilizam campanha publicada nem credenciais/ids externos, e `valid: true` não concede autorização editorial;
- os fluxos de produção existentes da Multitrack Hub em `marcas/multitrackhub/` continuam identificados como integrações separadas e não foram alterados.

A fixture genérica (`fixture-project`) permanece para testar variações de idioma e formato. Trabalho possível remanescente, não autorizado por esta integração: novos casos de pipeline para outros formatos/perfis, evolução do contrato de caso e qualquer consumo do agregador pelo Temporal (bloqueado).

## 4. Piloto mínimo de composição com títulos editáveis e estilos visuais — concluído em 13/11/2026

> O piloto mínimo de composição com títulos editáveis e estilos visuais reutilizáveis foi autorizado, implementado e integrado via opções `--text-overlays <plano.json>` e `--visual-style <estilo.json>` na CLI `tools/render_pipeline.py`. Detalhes e evidências em [ESTADO-ATUAL.md](ESTADO-ATUAL.md), seções Piloto de composição com títulos editáveis e Estilos visuais reutilizáveis, e em [tools/render/README.md](../../tools/render/README.md).

Critérios de conclusão atendidos:
- **Reaproveitamento do visual**: corrigir ou revisar o título textual na sobreposição ou alterar o estilo visual não exige regenerar nem alterar os assets visuais, o pacote canônico de execução, a legenda sincronizada `.srt` ou o roteiro de narração `.txt`;
- **Origem única e contratos**: `TextOverlayPlan` v1 e `VisualStyle` v1 com validação pura na `platform` e espelhos draft-07 (`platform/schemas/text-overlay-plan.schema.json` e `platform/schemas/visual-style.schema.json`), com intervalos derivados do `CreativeExecutionPackage` canônico e estilo desacoplado de `caseId` (compartilhável entre Marca Salão e Multitrack Hub);
- **Posicionamento e renderização**: títulos aplicados na região superior do quadro com cores hexadecimais convertidas para ASS, fonte configurável e margens superior e horizontais protegidas, preservando as legendas inferiores;
- **Política de áudio e inspeção**: MP4 gerado estritamente sem áudio (`-an`, 0 faixas de áudio), inspecionado e validado via FFprobe;
- **Transacionalidade e rastreabilidade**: promoção atômica, lock com revalidação de colisão sob disputa de destino vazio, e manifesto versionado `delivery-manifest.json` com caminhos, tamanhos e SHA-256 recalculados na leitura direta dos arquivos promovidos (incluindo `textOverlayPlan` mesmo com `overlays: []` e `visualStyle`);
- **Prova visual automatizada**: testes de regressão e inspeção comparativa de quadros (MAE) comprovando isolamento da alteração na região superior tanto na troca de texto quanto na troca de estilo visual.

## 4b. Inventário de mídia de ponta a ponta (`AssetManifest` v1) — concluído em 13/11/2026

> O inventário de mídia de ponta a ponta foi autorizado, implementado e integrado via `tools/prepare_asset_manifest.py`, `--asset-manifest <inventario.json>` e `--check-assets` em `tools/render_pipeline.py`, mantendo retrocompatibilidade integral de `--assets`. Detalhes e evidências em [ESTADO-ATUAL.md](ESTADO-ATUAL.md), seção Inventário de mídia de ponta a ponta (AssetManifest v1), e em [tools/render/README.md](../../tools/render/README.md).

Critérios de conclusão atendidos:
- **Montagem e deduplicação (`prepare_asset_manifest.py`)**: converte associação existente em inventário canônico, deduplica arquivos físicos repetidos, calcula tamanho em bytes e SHA-256 e registra `origin` e `license` (padrão `pending`), preservando os arquivos de origem intactos;
- **Prévia (`--plan-only --asset-manifest`)**: valida referências do inventário e exibe os vínculos na ordem da timeline sem ler mídias nem exigir FFmpeg;
- **Verificação prévia (`--check-assets`)**: verifica contenção na raiz, bytes, SHA-256, dimensões e compatibilidade de duração de vídeo via FFprobe exatamente uma vez por asset único, sem criar diretório de saída;
- **Render e rastreabilidade (`--asset-manifest --output-dir`)**: copia e revalida os bytes verificados em staging (`verified-assets/`), combina com `--text-overlays` e `--visual-style`, gera MP4 sem áudio (`-an`), legendas queimadas, `.srt` e narração `.txt` separados, promove `*-asset-manifest.json` e registra no `delivery-manifest.json` e relatório de execução;
- **Falha segura antes do FFmpeg**: adulteração de byte (`ASSET_HASH_MISMATCH`), arquivo ausente/corrompido, vídeo curto (`ASSET_VIDEO_TOO_SHORT`) e falhas de promoção preservam integralmente entregas anteriores.

Continua bloqueado até deliberação específica: produção de campanhas reais, fornecedores, áudio/TTS, Temporal e deploy.

## 4c. Produção de vídeo por entrada única (`VideoRequest` v1 + `tools/produce_video.py`) — concluído em 13/11/2026

> O titular autorizou em 13/11/2026 uma entrega completa: descrever as cenas em um JSON, conferir a prévia e exportar o vídeo para os perfis escolhidos, com implementação, testes, render de prova, CI e documentação na mesma rodada, e integração à main após os gates. **Integrada na main pelo merge commit `2ba0ee010a24a6183a57e0d67d2214228b033aa3`** (branch `codex/produce-video-single-input-v1`). Detalhes e comandos em [tools/produce/README.md](../../tools/produce/README.md) e [tools/render/README.md](../../tools/render/README.md), seção Produção por entrada única.

Critérios de conclusão atendidos:
- **Entrada única**: contrato `VideoRequest` v1 puro (`platform/src/video-request-contract.ts`, `validate-video-request.ts`, espelho draft-07 `video-request.schema.json` com paridade Ajv) e compilador puro `compile-video-request.ts` que deriva `Composition`, `BeatPlan`, `OutputPlan`, `CreativeExecutionPackage`, associação de mídia e títulos por perfil, resolvendo cada perfil apenas pelo catálogo (`resolveOutputPlan`), respeitando a allowlist do projeto e validando pelo pipeline canônico; casos gerados como rascunhos editoriais;
- **Prévia** (`--plan-only`): perfis resolvidos, duração total, tempos por cena, mídias necessárias e avisos, sem FFmpeg e sem gravação;
- **Exportação**: `tools/produce_video.py` prepara e verifica o `AssetManifest` por perfil (origem/licença por material via `build_asset_manifest_from_registry`) e chama o pipeline local existente; um único pedido gera os três destinos (`instagram-reels-video`, `facebook-reels-video`, `youtube-shorts`) em 9:16 a 30 fps, MP4 sem áudio, SRT e narração TXT;
- **Revisão e recuperação**: `--profile` reexporta um perfil após corrigir cena ou título com promoção transacional; falha de um perfil preserva a entrega anterior e não impede os demais; `index.json` verificável com caminhos válidos após a limpeza do staging; exit ≠ 0 quando algum perfil falha;
- **Prova reproduzível**: exemplos versionados das duas marcas em `tools/produce/examples/`, gerador `tools/make_request_media.py`, seis vídeos inspecionados por FFprobe (1080×1920@30, H.264/yuv420p, 14 s, 0 áudio), 48 hashes conferidos, SRT/TXT válidos, reexportação de um perfil com reutilização de mídia (hash do inventário idêntico) e segundo pedido Multitrack Hub pelo mesmo comando;
- **Gates**: typecheck, contratos e suíte da platform verdes; suíte Python com `REQUIRE_RENDER=1`; CI de render real em Ubuntu e Windows (`.github/workflows/local-render-validation.yml`) com prova do `produce_video`; API pública `["validateComposition"]` inalterada.

Continua bloqueado até decisão explícita: produção de campanhas reais, mídia real, fornecedores, áudio/TTS, publicação, Temporal e deploy. A aprovação editorial e a publicação seguem o fluxo vigente.

## 4d. Painel local de vídeo pelo navegador (Video Studio) — concluído em 13/11/2026

> O titular autorizou em 13/11/2026 uma entrega completa para criar, revisar e exportar um vídeo pelo navegador usando o pipeline existente, com implementação, testes, prova em navegador, CI e documentação na mesma rodada, e integração à main após os gates. **Integrada na main pelo merge commit `8fec01cb2bb4094f7a04ae617ea157ba449fb54d`** (branch `codex/video-studio-local-v1`). Comando: `python tools/video_studio.py --port 8765` (abra `http://127.0.0.1:8765`). Detalhes em [tools/produce/README.md](../../tools/produce/README.md), seção Painel local (Video Studio).

Critérios de conclusão atendidos:
- **Painel local** (`tools/video_studio.py` + `tools/studio/`): servidor HTTP stdlib em `127.0.0.1`; seleção de `ProjectManifest`, perfis do catálogo + allowlist com resolução/FPS/disponibilidade local; cadastro de mídia reutilizável com origem/licença; editor de cenas (adicionar/editar/remover/reordenar; duração, legenda, título, narração); rascunho `VideoRequest v1` (salvar/reabrir/exemplos); prévia via `produce_video.py --plan-only --json` sem FFmpeg; exportação em segundo plano com resultado por perfil; assistir MP4 e baixar MP4/SRT/TXT por referências verificadas nos manifestos; reexportar somente um perfil;
- **Segurança**: Host/Origin validados nas escritas; entradas/saídas confinadas à raiz (`.workspace/`); arquivos servidos apenas por referências dos manifestos promovidos; processos com argumentos estruturados; validação/render/promoção permanecem no pipeline existente;
- **Preservação da última entrega válida**: `merge_index` corrigido para registrar `lastAttempt` e `lastValidDelivery` separadamente, ler índices v1, validar o dono do destino, serializar exportações concorrentes (lock), gravar por substituição atômica e reconciliar pelos manifestos promovidos; uma reexportação que falha mostra o erro e continua abrindo a entrega anterior com hashes preservados;
- **Prova em navegador** (Playwright, checkout local): exemplo Marca Salão carregado, cena editada, prévia conferida, três destinos exportados, MP4 reproduzido no painel, SRT/TXT baixados; exemplo Multitrack Hub pelo mesmo fluxo (seleção por projeto); reexportação de um perfil após alterar título com reutilização de mídia (hash do inventário idêntico); falha provocada com mídia indisponível mostra o erro e ainda abre o vídeo anterior com hashes preservados; FFprobe confirma 1080×1920, 30 fps, duração esperada e zero faixas de áudio;
- **Gates**: suíte da platform e suíte Python com `REQUIRE_RENDER=1` (inclui `test_video_studio.py` e a regressão do índice); CI de render real em Ubuntu e Windows com prova HTTP do painel. API pública da platform inalterada.

Continua bloqueado até decisão explícita: produção de campanhas reais, mídia real, fornecedores, áudio/TTS, publicação, Temporal e deploy. O painel produz arquivos locais para revisão; a aprovação editorial e a publicação seguem o fluxo vigente.

## 4e. R003 — módulo local de carrosséis no painel — concluído em 13/11/2026

> O titular autorizou em 13/11/2026 implementar o R003 (carrosséis locais acessíveis pelo painel existente), com código, testes, prova no navegador, CI e documentação na mesma rodada, e integração à main após os gates. **Integrada na main pelo merge commit `7902e569360e76fc4f18fd4bda82800bf96615ad`** (branch `codex/r003-carousel-local-v1`). Comando do painel: `python tools/video_studio.py --port 8765` (aba **Carrosséis**); CLI: `python tools/produce_carousel.py --input <pedido> --plan-only|--output-dir <entrega> --json`. Detalhes em [tools/produce/README.md](../../tools/produce/README.md), seção Carrosséis (R003).

Critérios de conclusão atendidos:
- **Entrada única** `CarouselRequest v1` (id, projeto, perfil de imagem, cadastro reutilizável de mídias com origem/licença, cards ordenados com id/título/corpo/mídia opcionais); exemplo com capa, conteúdo e fechamento com CTA; texto editável no pedido;
- **Validação e prévia**: schema draft-07 + validador puro + paridade Ajv; `resolveOutputPlan` + allowlist resolvem `instagram-feed-image-square` (geometria do perfil); prévia informa ordem, geometria e erros sem FFmpeg e sem gravação; overflow de texto indica o card;
- **Render local**: JPEGs 1080×1080 com layout reutilizável (margens, contraste, quebra de linha); mídias de origem preservadas ao editar textos e reexportar;
- **Entrega**: nomes numerados, ZIP na mesma ordem, manifesto com id/dimensões/caminhos/tamanhos/SHA-256; promoção sob lock preservando a última entrega válida; remoção de card reflete a nova ordem no conjunto e no ZIP;
- **Painel**: abas Vídeos/Carrosséis com editores próprios; editor de carrossel carrega exemplo, salva/reabre, adiciona/reordena cards, revisa e exporta; imagens na ordem do manifesto com download individual e do ZIP; `export_status` corrigido (finaliza uma vez, resultado em cache em consultas repetidas — regressão coberta);
- **Prova em navegador**: exemplo Marca Salão editado/reordenado, exportado, ZIP baixado (JPEG/dimensões/ordem/hashes conferidos); Multitrack Hub pelo mesmo fluxo; edição de texto reexportada (texto novo na imagem, hash da mídia de origem inalterado); falha com mídia indisponível preserva a entrega anterior; pedido inválido e remoção de card cobertos;
- **Gates**: suíte da platform e suíte Python verdes; CI em Ubuntu/Windows com prova de carrossel preservando a prova de render de vídeo. API pública inalterada.

Continua bloqueado até decisão explícita: produção de campanhas reais, mídia real, fornecedores, publicação, Temporal e deploy. O painel produz arquivos locais para revisão; aprovação editorial e publicação seguem o processo vigente.

## 4f. Aba Motion (contorno animado) no painel — concluído em 13/11/2026

> O titular autorizou em 13/11/2026 entregar a aba Motion no painel existente: abrir um pedido de vídeo, marcar uma região da cena, configurar um contorno animado, conferir a prévia e exportar o MP4 pelo pipeline atual, com código, testes, prova no navegador, CI e documentação na mesma rodada. **Integrada na main pelo merge commit `a825ded6dcfcb33ac4d77f0d315ca311147e2eb5`** (branch `codex/motion-outline-v1`). Comando do painel: `python tools/video_studio.py --port 8765` (aba **Motion**); CLI: `python tools/produce_video.py --input <pedido> --motion-plan <plano.json> --plan-only|--output-dir <entrega> [--profile <id>] --json`.

Critérios de conclusão atendidos:
- **Contrato** `MotionPlan v1` separado do pedido, com `requestId` e efeitos por `sceneId` (região relativa, cor, espessura, intervalo relativo à cena; um efeito por cena); schema draft-07 + paridade Ajv; tempos absolutos pela timeline canônica; valida referência/geometria/intervalo/compatibilidade (cena com zoom → incompatível);
- **Comando** `--motion-plan` em `--plan-only --json` e na exportação (inclusive `--profile`); prévia informa cenas/regions/intervalos resolvidos sem FFmpeg; parâmetros do efeito independentes de fornecedor/LLM;
- **Composição**: contorno sobre o quadro enquadrado antes de títulos/legenda, entrada/saida suaves na janela; recorte inicial = região fixa em cena sem zoom; MP4 sem áudio + SRT + TXT pelo adaptador local;
- **Entrega**: plano canônico promovido com o vídeo, caminho/tamanho/SHA-256 no manifesto, intervalos/regiões no relatório; staging/lock/rollback/`lastValidDelivery` reutilizados;
- **Aba Motion**: carrega rascunho/exemplo, escolhe cena, marca retângulo sobre a prévia enquadrada, ajusta intervalo/cor/espessura, mostra onde o contorno aparece, salva/reabre o plano, exporta um perfil e assiste; jobs com consultas simultâneas finalizando uma vez com o mesmo resultado; última entrega válida preservada em falha;
- **Prova**: agenda fictícia, horário marcado no navegador, quadros antes/durante/depois conferidos; recoloração/posição reexportada com mudança na região esperada e hashes de mídia/SRT/TXT inalterados; Multitrack Hub pelo mesmo editor; região inválida/intervalo fora/referência inexistente/consulta simultânea/falha que preserva cobertos; FFprobe 1080×1920@30, zero áudio;
- **Gates/CI**: platform + suíte Python verdes; prova do efeito no CI de render real em Ubuntu/Windows junto das regressões de vídeo e carrossel; README com caminho mais curto; resumo desatualizado do R003 em ESTADO-ATUAL corrigido.

Continua bloqueado até decisão explícita: produção de campanhas reais, mídia real, fornecedores, publicação, Temporal e deploy. Aprovação editorial e publicação seguem o processo vigente.

## 4g. Primeira versão utilizável do Studio local (Projetos, Trabalhos e retomada) — concluído em 13/11/2026

> O titular autorizou fechar a primeira versão utilizável do Studio local com cadastro de projetos, trabalhos persistentes, produção e retomada de Vídeo, Carrossel e Motion, testes, prova em navegador, CI e documentação na mesma entrega (branch `codex/studio-usable-v1`). Comandos: `python tools/video_studio.py --check --json` e `python tools/video_studio.py --port 8765`. Detalhes em [tools/produce/README.md](../../tools/produce/README.md).

Critérios de conclusão atendidos:
- **Projetos (`ProjectManifest` v1)**: formulário no painel valida o manifesto pelo núcleo da `platform` antes da gravação em `.workspace/studio/projects/`, exibe badge diferenciando projetos cadastrados de exemplos versionados e filtra automaticamente os destinos pelo catálogo + allowlist + módulo aberto (`video`, `carousel`, `motion`);
- **Trabalhos persistentes e mídias compartilhadas**: tela inicial **Trabalhos & Projetos** lista trabalhos recentes com `Reabrir`, cria trabalhos novos (`POST /api/works/create`) e demonstração guiada em 1 clique (**Marca Salão** / **Multitrack Hub**), derivando automaticamente rascunhos, pasta `media/` compartilhada e pastas `deliveries/` dentro de `.workspace/studio/works/<id>/` sem digitar caminhos nem editar JSON;
- **Retomada integral entre reinícios**: documentos de Vídeos (`VideoRequest`), Carrosséis (`CarouselRequest`) e Motion (`MotionPlan` multi-cena com alternância entre cenas sem zoom via `#m-scene-select` e `#m-effects-summary`) são gravados de forma atômica; fechar e reiniciar o servidor HTTP mantém mídias, alterações não exportadas, histórico de `lastAttempt` (incluindo detecção `interrupted` de jobs órfãos e alertas `failed`) e `lastValidDelivery` preservada;
- **Compatibilidade Windows & Gates**: tratamento transparente de caminhos longos no Windows (`render_local.fs_path`), `926/926` testes da `platform`, `143/143` testes Python com `REQUIRE_RENDER=1`, prova end-to-end em navegador Google Chrome real via CDP e prova HTTP ampliada no CI (Ubuntu e Windows). API pública da `platform` inalterada.

Continua bloqueado até decisão explícita: produção de campanhas reais, mídia real, fornecedores externos, áudio/TTS, publicação, Temporal de produção e deploy. O painel local destina-se apenas a criação e revisão local.

## 5. Separar as decisões editoriais da execução técnica

Para a NS-001, tratar as pendências apontadas nos documentos da própria campanha. Uma evidência técnica aprovada não aprova o briefing, o hook, o roteiro ou a publicação.

Na próxima validação funcional, registrar o commit executado, alterações locais, ambiente, fixture, comandos, resultados e evidências. Não atribuir retroativamente um commit à execução antiga.

## 6. Preparar a proposta de autorização para execução real em produção da validação de Composition no Temporal

> Próxima entrega recomendada após a integração da execução local de TEMPORAL-02 (12/11/2026, merge `5376890`): **preparar a proposta completa de autorização para execução real (produção/remota) da validação de Composition no Temporal, sem iniciar implementação automaticamente.**

A proposta deve delimitar escopo, componentes, riscos, evidências exigidas e critérios de ratificação, reaproveitando o que já está integrado e ratificado (fronteira pública, input/preflight, Activity, Workflow em escopo estrito, Retry Policy, execução local completa com replay e gate Elephant–Goldfish) e o precedente de gates do R002 e da execução local (reprodução limpa, inspeção técnica real, prova transacional, hashes e documentação no mesmo marco). É trabalho de proposta: Worker de produção, servidor remoto, namespace de produção e deploy continuam bloqueados; a execução real depende de decisão explícita e separada do titular.

## 7. Executor local simulado do CreativeExecutionPackage — concluído em 12/11/2026

> O executor local simulado foi autorizado, implementado e integrado na main pelo merge commit `2824728300f20c89fe02717e29130895996ae85b` em 12/11/2026, a partir da branch `codex/simulated-execution-runner-v1`. Detalhe e evidências em [ESTADO-ATUAL.md](ESTADO-ATUAL.md), seção Executor local simulado v1.

Critérios atendidos: consumo do pacote canônico com validação; estados e eventos determinísticos sem tempo real; artefatos somente textuais/JSON com hashes SHA-256; escrita transacional com confinamento e preservação da saída anterior; falha e cancelamento controlados; retomada segura baseada em relatório anterior; multicase com isolamento de falha; os dois consumidores reais executados; API pública preservada; CI verde nos quatro jobs.

## 8. Primeiro adaptador de renderização local — integrado na main (12/11/2026)

> O titular autorizou explicitamente em 12/11/2026, em duas rodadas: (1) implementar e testar o **primeiro adaptador de renderização local que consome o `CreativeExecutionPackage` v1**, com vídeos locais de prova e dados fictícios, documentação e publicação da branch técnica; (2) corrigir a promoção e o relatório, acrescentar validação com FFmpeg no GitHub Actions e **integrar à main depois que os critérios de aceite fossem cumpridos**.

Estado: **integrado na main** pelo merge commit `5be61b8cb3c1894088aae950a81469633447c45f` (branch `codex/local-render-adapter-v1`, HEAD `e52c88df927a9dddbac09fb175e2ebe4329becd6`, base `fbaf2b76943771bbc1a45c1768f39edbfcf67008`). Critérios cumpridos: renders reais de 14 s e 15 s em 1080×1920@30 com zero faixas de áudio comprovadas por FFprobe; relatório com caminhos finais conferido arquivo a arquivo; rejeição de staging incompatível antes de qualquer escrita; preservação da entrega anterior em falha e exclusão de promoções concorrentes por lock; typecheck, suíte da platform (818/811/0/7), suíte Python (54 testes OK com `REQUIRE_RENDER=1`) e CI de render real verde na branch (run [43309423710](https://github.com/Jonatasbottaro/marcasalao-marketing/actions/runs/43309423710), Ubuntu e Windows); gate em worktree limpa e pós-merge no checkout principal verdes. Detalhe, medições FFprobe, provas de preservação e evidências em [ESTADO-ATUAL.md](ESTADO-ATUAL.md), seção Adaptador de render local de prova, e em [tools/render/README.md](../../tools/render/README.md).

O que a entrega prova: pacote validado pelo núcleo puro (`validateLocalRenderInput` reutilizando `validateCreativeExecutionPackage`); associação explícita beats → assets com contenção real; render FFmpeg local das duas fixtures verticais (14 s e 15 s, 1080×1920@30, H.264/yuv420p, zero áudio); legenda queimada + SRT UTF-8 + narração TXT derivados do pacote; inspeção FFprobe antes da promoção; staging exclusivo validado antes de escrita, promoção exclusiva por lock com backup e restauração da entrega anterior em falha (backup preservado se a restauração falhar); timeouts curtos com diagnóstico; mesma CLI para as duas marcas, diferenças somente nos pacotes e assets; CI dedicado de render real em Ubuntu e Windows que falha se faltar ferramenta/ponte ou se os testes obrigatórios forem pulados.

Continua bloqueado até decisão explícita: renderização de campanha real, mídia real, fornecedores, publicação, Temporal e qualquer ampliação do recorte inicial do adaptador. O executor `simulation` e a API pública da platform permanecem intactos.

## Tarefas secundárias permitidas

1. Reconferir a main e as PRs abertas antes de propor qualquer integração; R001, BeatPlan v1, a regra permanente de armazenamento, a orientação de segurança de worktrees e o contexto atualizado já estão integrados, e nenhuma combinação entre planos está autorizada.
2. Decidir se as cinco branches documentais já integradas podem ser arquivadas, sem exclusão automática: `atualiza-contexto-beat-plan-v1`, `atualiza-contexto-regra-armazenamento`, `reconcilia-beat-plan-v1`, `regra-armazenamento-workspace` e `seguranca-worktrees-workspace`. A limpeza de 11/11/2026 já removeu as 13 superseded e a obsoleta `.worktrees`; o detalhe e os SHA de recuperação estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md).
3. Decidir o destino da PR #1 (`ai-memory-integration`) como tarefa própria: é a única branch com trabalho real pendente (19 arquivos ausentes da main, incluindo um workflow de CI novo), conflita em `.ai-memory.toml`, `.gitignore` e `AGENTS.md` e está 82 commits atrás. Exige reconciliação com o `AGENTS.md` atual e autorização específica do CI.
4. Não reintroduzir a convenção `.worktrees/`: a branch que a propunha foi excluída por contradizer a regra permanente, e a orientação de segurança aproveitável já está integrada sob `.workspace/` por `79fd5da`.

Os limites do que não fazer agora estão em [ESTADO-ATUAL.md](ESTADO-ATUAL.md); não repeti-los aqui.

## Critério para encerrar uma tarefa

Entregar o comportamento ou documento alterado, a referência Git, as verificações realizadas e as limitações. Registrar a próxima ação concreta no contexto, preservando o histórico e o trabalho das outras branches. Cumprir o handoff obrigatório da regra de armazenamento em [AGENTS.md](../../AGENTS.md), incluindo a confirmação textual de que nada foi criado ou mantido fora da raiz real do checkout nesta máquina e a declaração de qualquer exceção como bloqueio.
