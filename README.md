# Marca Salão Marketing

Repositório de marketing do Marca Salão, com fluxos também organizados para a Multitrack Hub e um núcleo reutilizável de produção de conteúdo em evolução.

## Contexto e continuidade

Comece por [docs/contexto/README.md](docs/contexto/README.md). O [estado atual](docs/contexto/ESTADO-ATUAL.md) diferencia o código integrado na main, as alterações em revisão e as pendências editoriais. As [próximas etapas](docs/contexto/PROXIMOS-PASSOS.md) e o [handoff](docs/contexto/HANDOFF.md) orientam a retomada entre agentes e computadores.

A arquitetura e os comandos do núcleo ficam em [platform/README.md](platform/README.md). As decisões de arquitetura são registros históricos; não substituem a verificação do código e das PRs.

## Estrutura
- `00-briefings/` - Briefings de campanha: dor, impacto, evidência e limites de promessa antes de produzir
- `01-insta-stories/` - Cards 1080x1920 para Instagram/WhatsApp com guia CapCut
- `02-reels-shorts/` - Vídeos verticais para Reels/Shorts/TikTok
- `02-hooks/` - Hooks em rascunho por campanha, derivados dos briefings
- `03-youtube-pdf/` - PDFs e apresentações para YouTube/Site
- `03-roteiros/` - Roteiros por campanha: cenas, textos de tela e narração em rascunho
- `04-legendas/` - Legendas, roteiros, scripts de áudio, pacotes de publicação, calendário editorial e matriz UTM
- `05-review-portal/` - Portal estático de revisão humana (build determinístico, abre via `file://` ou servidor local)
- `schemas/` - JSON Schema dos contratos multi-tenant (brand-kit, guardrails)
- `tenants/` - Contratos por marca da fábrica de vídeo: brand-kit, guardrails, fixtures e campanhas
- `marcas/` - Materiais, configurações e integrações específicas de Marca Salão e Multitrack Hub
- `platform/` - Contratos, schemas, validação, relatórios, CLIs e testes do núcleo reutilizável
- `docs/contexto/` - Contexto compartilhado, estado atual, próximos passos e procedimento de retomada

## Fábrica de vídeo multi-tenant (contratos → render → pacotes → release)

Pipeline programático que transforma contratos JSON versionados em pacotes de vídeo prontos para publicação manual, para N marcas sem alterar o motor de render. Estado atual: **4 tenants, 8 campanhas e 16 módulos de testes** no gate do CI. Cada campanha entrega MP4 1080×1920@30 (sem faixa de áudio quando o tenant proíbe), SRT, narração TXT, storyboard, `manifest.json` com hashes SHA-256 e `derivatives.json` (cover, 1:1, 16:9); o pacote social sai com `autoPublish: false`, o calendário editorial nasce `aguardando_aprovacao_titular` e o portal de revisão é somente leitura. **Nenhuma ferramenta deste repositório publica, agenda ou cria rascunho nas redes: a publicação é sempre manual e exige autorização específica do titular.** Arquitetura completa em [docs/arquitetura-fabrica.md](docs/arquitetura-fabrica.md).

| Tenant | Marca | Preset | Domínio | Áudio | Campanhas |
| --- | --- | --- | --- | --- | --- |
| `marca-salao` | Marca Salão | `saas-demo` | marcasalao.com.br | Proibido (`-an`) | 2 |
| `multitrack-hub` | Multitrack Hub | `shorts-completo` | multitrackhub.com.br | Permitido (opcional) | 3 |
| `meu-salao` | Meu Salão | `saas-demo` | meusalao.com.br | Proibido | 2 |
| `estudio-flow` | Estúdio Flow | `saas-demo` | estudioflow.com.br | Proibido | 1 |

Comandos rápidos (a partir da raiz do checkout):

```bash
python tools/tenant_validator.py --all --json           # 1. validar contratos (brand-kit, guardrails, fixture)
python tools/factory_cli.py list --json                 # 2. descobrir tenants e campanhas
python tools/factory_cli.py render --all --json         # 3. renderizar em lote (MP4, SRT, narração, storyboard, manifesto)
python tools/audio_tts.py --tenant multitrack-hub \
  --output .workspace/tmp/audio-mth/bed-30s.wav --duration 30 --mode ambient-bed   # 3a. trilha (só tenant com áudio permitido)
python tools/derivative_formats.py --all --json         # 4. derivados cover/1:1/16:9 + derivatives.json
python tools/publish_pack.py --all                      # 5. pacotes sociais (autoPublish: false)
python tools/campaign_calendar.py --start-date 2026-11-23 --json   # 6. calendário editorial + matriz UTM
python tools/review_dashboard.py --build --json         # 7. gerar o portal de revisão (05-review-portal/)
python tools/review_dashboard.py --serve --port 8765    # 7a. revisar no navegador (somente leitura)
python tools/release_audit.py --json                    # 8. auditoria de prontidão (7 domínios; avisos não reprovam)
python tools/release_audit.py --strict --json           # 9. gate de release (avisos também reprovam)
python tools/release_audit.py --strict --report-out .workspace/tmp/release-audit.json   # 9a. gravar o relatório
python tools/devlog_sync.py --json                      # 10. consolidar devlogs no contexto_projeto.md
```

Checklist de operação manual: alinhar a estação (`git fetch origin --prune && git pull --ff-only`) → validar contratos → renderizar → (opcional) trilha `audio_tts` apenas para `multitrack-hub` → derivados → pacotes → calendário → portal → auditoria `release_audit` → gate `--strict` → consolidar devlogs.

Protocolo de revisão humana e publicação: o portal `05-review-portal/` e o calendário editorial são instrumentos de **revisão e proposta** — o titular aprova, e a publicação nas redes é feita manualmente por ele (ou por ferramenta externa mediante autorização específica). `autoPublish: false` e `statusEditorial: "aguardando_aprovacao_titular"` são verificados pelo gate de release; nada neste repositório publica, agenda ou cria rascunho por conta própria. Novo nicho/tenant: [docs/guia-novo-nicho.md](docs/guia-novo-nicho.md).

## Ferramentas
- CapCut (mobile/desktop)
- Drift - https://cutwire.org/drift
- FFmpeg

## Demo

Acesse a demonstração:
https://marcasalao.com.br/gestor

As credenciais de demonstração não são mantidas neste repositório.
Solicite um acesso de demonstração ao responsável pelo projeto.

## Padrão de entrega
Vídeos sem áudio, com legendas nas cenas, arquivo SRT e texto de narração separado para geração de áudio em ferramenta externa. Não preservar o áudio original nem gerar áudio no editor. Vídeos de teste não são campanhas finais aprovadas.

## Produzir o primeiro vídeo (entrada única)

Descreva as cenas em um JSON, confira a prévia e exporte para os perfis escolhidos. O mesmo pedido gera `instagram-reels-video`, `facebook-reels-video` e `youtube-shorts` a partir da mesma fonte de cenas e mídia. Guia completo em [tools/produce/README.md](tools/produce/README.md).

```bash
cd platform && npm ci && npm run build && cd ..   # FFmpeg/FFprobe no PATH
python tools/make_request_media.py --input tools/produce/examples/marca-salao-social-reel.video-request.json
python tools/produce_video.py --input tools/produce/examples/marca-salao-social-reel.video-request.json --plan-only --json
python tools/produce_video.py --input tools/produce/examples/marca-salao-social-reel.video-request.json --output-dir .workspace/archives/primeiro-video --json
```

Cada perfil entrega MP4 sem áudio, SRT, narração em TXT, pacote canônico, inventário de mídia e `delivery-manifest.json`; o `index.json` reúne o estado por perfil. Os casos gerados são rascunhos editoriais, não campanhas aprovadas.

### Painel local (Video Studio)

Para criar, revisar, retomar e exportar pelo navegador, confira o ambiente e abra o painel local:

```bash
python tools/video_studio.py --check
python tools/video_studio.py --port 8765
# abra http://127.0.0.1:8765
```

Na tela inicial (**Trabalhos & Projetos**):
- Confira a prontidão do ambiente (`5/5` verificações de Python, Node, build da `platform`, FFmpeg e FFprobe) ou execute uma **Demonstração guiada** em 1 clique (**Marca Salão** ou **Multitrack Hub**).
- Cadastre projetos (`ProjectManifest` v1) validados pelo núcleo sem editar JSON, distinguindo projetos cadastrados dos exemplos versionados.
- Crie e reabra **Trabalhos** persistentes em `.workspace/studio/works/<id>/`: rascunhos, mídias compartilhadas entre Vídeo, Carrossel e Motion e pastas de entrega têm caminhos gerados automaticamente a partir dos IDs, sem digitar caminhos.
- Veja apenas destinos compatíveis com o projeto (allowlist + catálogo) e com o módulo aberto (**Vídeos** 9:16@30, **Carrosséis** 1:1 ou **Motion** 9:16@30).
- Feche e reabra o painel retomando textos, estilos, mídias, seleções multi-cena e entregas válidas; tentativas falhas ou interrompidas exibem aviso próprio enquanto preservam `lastValidDelivery`. O servidor escuta somente em `127.0.0.1`, valida Host/Origin e confina tudo à raiz. Guia em [tools/produce/README.md](tools/produce/README.md).
- Na aba **Planejamento**, transforme uma ideia em texto livre no fluxo guiado em 3 etapas (**1. Ideia e briefing** -> **2. Hook, roteiro e cards** -> **3. Aplicação aos editores**), usando preenchimento **Manual**, **Copiar e importar** (prompt estrito e validação do contrato `PlanningSuggestion` v1 antes de incorporar) ou **Modelo local opcional** (`POST /v1/chat/completions`, `qwen3:8b`, desativado por padrão), com preservação de edições manuais, checagem de políticas por projeto, proteção de cenas com mídia local pendente (`pending_media`), sugestões clicáveis no Motion e aplicação seletiva para Ficha Editorial, Vídeos, Carrosséis, Motion e canais.
- Em cenas e cards do Planejamento, use **Preparar imagem** para abrir um pedido visual revisável a partir do descritor da peça, importar ou gerar candidatos, comparar opções, selecionar uma versão e aplicá-la pela prévia de diferenças (fluxo completo abaixo).
- Na aba **Mídias**, gerencie a biblioteca do trabalho: importação de imagens autorizadas (validação pelo conteúdo, SHA-256, origem e licença), versões imutáveis com histórico, referências visuais reutilizáveis (`VisualAnchor` v1) e pedidos visuais (`ImageRequest` v1) com candidatos e tentativas.
- Na aba **Revisão & Entrega**, registre a ficha editorial do trabalho (`editorial.json`) e os textos de publicação por canal (separados do `.srt` de legendas e do `.txt` de narração), revise vídeos, carrosséis e motion vinculados à versão da entrega com histórico de decisões (incluindo detecção de entregas legadas/externas `unlinked` e revalidação localizada por canal ou peça), confira a origem dos materiais utilizados (ilustrações geradas distinguídas de capturas/evidências) e gere o **pacote ZIP de entrega** transacional com pastas separadas para Vídeo (`video/<perfil>/`) e Motion (`motion/<perfil>/`), `package-manifest.json` e verificação SHA-256.

### Biblioteca de mídias por trabalho (Planejamento → Preparar imagem → Comparar → Aplicar → Exportar → Revisar → ZIP)

Cada trabalho tem uma biblioteca de mídia local (`.workspace/studio/works/<id>/media-library.json`) conectada ao Planejamento:

1. **Preparar imagem** — no Planejamento, uma cena ou card com `requiredMediaDescriptor` abre um pedido visual (`ImageRequest` v1) com prompt editável, finalidade, enquadramento e proporção derivada do perfil selecionado (9:16 → 1080×1920, 1:1 → 1080×1080). O texto exato que será enviado ao provedor é mostrado antes da confirmação; títulos, legendas e CTA permanecem nos campos editáveis da peça.
2. **Referência visual** — uma imagem importada pode virar `VisualAnchor` v1, vinculada pelo ID da versão e pelo SHA-256, com direção visual, elementos obrigatórios e elementos a evitar. A mesma referência serve a várias cenas/cards; cada pedido decide se ela será enviada ao provedor. Mudanças no texto do pedido ou na referência marcam os candidatos produzidos com a versão anterior.
3. **Importar ou gerar** — três caminhos por ação confirmada: importação manual (funciona sem rede e sem chave; serve para materiais de ferramentas externas como Google Flow, conforme as permissões do trabalho), simulador determinístico (fixtures e demonstração; materiais marcados como simulados) e Google Gemini opcional (configuração abaixo). Cada importação/geração cria uma versão com ID próprio, SHA-256, dimensões, origem, licença e proveniência (provedor, modelo, prompt, parâmetros, referência e hash do resultado).
4. **Comparar e selecionar** — os candidatos aparecem lado a lado com miniaturas; a seleção grava o vínculo no rascunho pelos campos atuais (`mediaId` + `media[]`) através do catálogo de mídia do Planejamento e da prévia de diferenças. O `AssetManifest` do render materializa caminho, origem, licença e hash da versão escolhida. A seleção de mídia é separada da aprovação da peça: só as peças que usam a mídia alterada pedem nova revisão; mídia compartilhada pode atualizar todos os vínculos de uma vez, identificando as peças consumidoras.
5. **Exportar → Revisar → ZIP** — os fluxos existentes seguem iguais: Vídeo e Motion em MP4 sem faixa de áudio + SRT + narração TXT; Carrossel em JPEGs na ordem do manifesto; Revisão & Entrega com origens dos materiais e ZIP transacional verificado por SHA-256.

```bash
python tools/video_studio.py --port 8765
# Planejamento -> cena/card -> Preparar imagem -> importar/gerar -> comparar -> selecionar -> aplicar
# Vídeos/Carrosséis/Motion -> exportar -> Revisão & Entrega -> aprovar -> Gerar ZIP de entrega
# Prova HTTP completa (CI e local, dados fictícios + simulador):
python tools/ci_media_library_proof.py --port 8797
```

**Google Gemini (opcional).** Defina `GEMINI_API_KEY` apenas no ambiente do processo antes de abrir o Studio; o painel mostra somente o estado da configuração (nunca a chave). Modelo configurável por `STUDIO_GEMINI_IMAGE_MODEL` (padrão `gemini-3.1-flash-image`), endpoint por `STUDIO_GEMINI_IMAGE_ENDPOINT` (padrão `https://generativelanguage.googleapis.com`) e timeout por `STUDIO_GEMINI_TIMEOUT_SEC` (padrão 120). O adaptador usa a API oficial `POST /v1/models/{modelo}:generateContent` com `responseModalities: ["TEXT","IMAGE"]` e `imageConfig.aspectRatio`; timeout, falta de credencial, cota, recusa, resposta sem imagem e arquivo inválido têm diagnósticos em português e nenhuma tentativa automática. Teste real com chave autorizada: abra o Studio com a chave no ambiente e use **Gerar com Google Gemini** em um pedido; no CI o Google é simulado.

**Adicionar outro adaptador.** Implemente uma classe em `tools/image_adapters.py` com `generate(prompt, geometry, ...)` retornando `{bytes, format, width, height, provider, model, simulated}`, registre o provedor em `provider_status()` e acrescente o ramo em `studio_media.generate_candidate`. Os contratos `VisualAnchor`/`ImageRequest` e os pedidos dos editores não mudam. A regra vigente de arte do Marca Salão via ComfyUI08 e seu guard de proveniência continuam valendo para o fluxo de produção oficial e publicação da marca; este adaptador atende ao fluxo de candidatos do Studio dentro do escopo autorizado.

### Exportação multiformato (YouTube horizontal 16:9 e Carrossel 4:5)

Além dos verticais 9:16 e do carrossel quadrado 1:1, o Studio local exporta **`youtube-video-horizontal` (1920×1080, 16:9, 30 fps, MP4 H.264)** e **`instagram-feed-image-portrait` (1080×1350, 4:5)**, sempre respeitando a allowlist do projeto. A exportabilidade local por módulo vem de uma **fonte compartilhada** (`platform/src/output-profiles/local-export.ts`), consumida pela CLI de perfis, pela API do Studio, pelo Planejamento, pela biblioteca de mídias e pelos seletores do painel — não há segundo dicionário de formatos. Perfis conhecidos sem render local mostram o motivo (geometria/fps fora do adaptador, ou Motion restrito ao vertical).

- **Vídeo horizontal**: selecione `youtube-video-horizontal` na tabela de perfis do editor de Vídeos (ou em `profiles` do `VideoRequest`) junto dos verticais; cada destino mantém pacote, pasta de entrega, relatório e estado de revisão próprios. Exporte apenas um perfil com `--profile` ou pelo seletor do painel. Uma falha no horizontal aparece naquele perfil e preserva as entregas válidas dos demais.
- **Enquadramento padrão**: `scale=<W>:<H>:force_original_aspect_ratio=decrease` + `pad` centralizado + `setsar=1` — a mídia nunca é distorcida; as áreas de preenchimento (letterbox/pillarbox) ficam em preto no vídeo e no tom do layout no carrossel. Títulos e margens escalam com a geometria (fonte/margem superior pela altura, margens horizontais pela largura), preservando os estilos existentes de 9:16; legendas queimadas mantêm proporção da altura e cabem na base do 16:9 (comprovado por medição de quadros nos testes).
- **Carrossel 4:5**: no Planejamento, escolha 1:1 ou 4:5 quando ambos estiverem na allowlist (seletor de formato do carrossel); o layout usa a geometria do perfil na medição de texto, margens, quebra de linha, desenho e manifesto. Texto que ultrapassa a área útil indica o card na prévia (`overflowCards`) e bloqueia a exportação preservando o conjunto válido anterior.
- **Motion permanece 9:16 nesta rodada**: o seletor e a prévia explicam o recorte; um `MotionPlan` enviado a um destino horizontal falha somente naquele perfil com `MOTION_LOCAL_UNSUPPORTED_GEOMETRY` (o contorno usa coordenadas relativas ao quadro final e exige configuração própria para outro enquadramento).
- **Pedidos de imagem**: a geometria do `ImageRequest` deriva do perfil selecionado (16:9 → 1920×1080, 4:5 → 1080×1350); ao mudar o destino, o diálogo mostra as dimensões da mídia atual e como ela será enquadrada, permitindo reaproveitar a versão existente ou preparar um candidato para o novo quadro (o contexto do pedido é atualizado e candidatos anteriores ficam marcados).
- **ZIP multiformato**: a aba Revisão & Entrega reúne vídeo vertical + horizontal + carrossel 4:5 + textos aprovados no mesmo pacote, com caminhos separados por modalidade/perfil e manifesto conferido contra os bytes do ZIP.

```bash
# Prévia e exportação horizontal por CLI (projeto com o perfil na allowlist):
python tools/produce_video.py --input <pedido.video-request.json> --profile youtube-video-horizontal --plan-only --json
python tools/produce_video.py --input <pedido.video-request.json> --profile youtube-video-horizontal --output-dir .workspace/archives/horizontal --json
# Carrossel 4:5:
python tools/produce_carousel.py --input <pedido.carousel-request.json> --profile instagram-feed-image-portrait --plan-only --json
python tools/produce_carousel.py --input <pedido.carousel-request.json> --profile instagram-feed-image-portrait --output-dir .workspace/archives/carrossel-4x5 --json
# Prova HTTP completa (CI e local): vertical + horizontal + 4:5 + ZIP + reinício
python tools/ci_multi_format_proof.py --port 8796
```

Matriz de formatos efetivamente comprovada nesta rodada (render real + FFprobe + navegador):

| Módulo | Perfil | Geometria | FPS | Áudio | Estado |
| --- | --- | --- | --- | --- | --- |
| Vídeo | `instagram-reels-video`, `facebook-reels-video`, `youtube-shorts` | 1080×1920 (9:16) | 30 | 0 faixas | comprovado |
| Vídeo | `youtube-video-horizontal` | 1920×1080 (16:9) | 30 | 0 faixas | comprovado |
| Carrossel | `instagram-feed-image-square`, `facebook-feed-image-square` | 1080×1080 (1:1) | — | — | comprovado |
| Carrossel | `instagram-feed-image-portrait`, `facebook-feed-image-portrait` | 1080×1350 (4:5) | — | — | comprovado |
| Motion | perfis de vídeo 9:16 | 1080×1920 | 30 | 0 faixas | comprovado (horizontal bloqueado com diagnóstico) |

### Edição de gravações e cortes por cena

Importe uma gravação **MP4 H.264** pelo navegador (aba Vídeos → **Importar gravação MP4**): o envio é em blocos, com limite de 256 MiB, validação por FFprobe (tipo, duração, dimensões, bytes, SHA-256, origem e licença) e promoção conjunta do arquivo + registro na biblioteca do trabalho. A mesma gravação pode ser recortada em **várias cenas**: cada cena de vídeo tem player mudo da fonte, **Marcar entrada/saída**, campos de tempo editáveis e **Reproduzir trecho**, com duração disponível, duração da cena e posição na montagem visíveis; trechos que ultrapassam a fonte mostram erro junto da cena. **Duplicar cena** reaproveita a fonte em outro trecho; reordenar preserva a janela e recalcula a posição. Salvar, recarregar e reiniciar o servidor recuperam as escolhas.

O corte vive no `VideoRequest v1` (`sourceStartMs` opcional por cena; saída derivada `sourceStartMs + durationMs`; pedidos legados partem de zero; omitido ≡ zero na versão efetiva). A prévia `--plan-only --json` mostra a janela da fonte distinta da posição na montagem, sem FFmpeg. O render aplica o corte com precisão de quadro mesmo entre keyframes (`-ss` de entrada + `setpts=PTS-STARTPTS`), confere o fim pedido contra a duração da faixa de vídeo (fim exato aceito; além do arquivo → `SOURCE_CUT_OUT_OF_RANGE` com cena, intervalo e duração disponível) e registra `sourceCuts` (trecho, identidade e hash da fonte) no manifesto e no relatório. Título, legenda e Motion seguem nos tempos da montagem; a exportação continua **MP4 sem faixa de áudio + SRT + narração TXT**. Alterar o início de uma cena marca `draft_outdated` os vídeos e Motion que usam a edição anterior (carrossel independente não é afetado); reexportar um perfil com duração/textos idênticos muda o quadro e o hash do MP4, preservando fonte/SRT/TXT e os arquivos do perfil fora da reexportação. O ZIP registra os cortes por peça e confere os hashes empacotados.

```bash
# Gravação fictícia de três trechos identificáveis (fixture do projeto):
python tools/make_request_media.py --input <pedido.video-request.json> --recording
# Prévia (fonte × montagem) e exportação Reels + YouTube horizontal do mesmo pedido:
python tools/produce_video.py --input <pedido.video-request.json> --plan-only --json
python tools/produce_video.py --input <pedido.video-request.json> --output-dir .workspace/archives/cortes --json
# Prova HTTP completa (CI e local): importação, cortes, quadros, reexportação, falha controlada, ZIP, reinício
python tools/ci_recording_cuts_proof.py --port 8798
```

### Carrosséis (R003)

Na aba **Carrosséis** do painel (ou dentro de um trabalho ativo), edite capa, conteúdo e fechamento com CTA reaproveitando a pasta de mídias do trabalho, confira a **prévia sem FFmpeg**, exporte os JPEGs 1080×1080 (1:1) ou 1080×1350 (4:5, quando o projeto permitir `instagram-feed-image-portrait`) e baixe o ZIP. Pela CLI:

```bash
python tools/make_request_media.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json
python tools/produce_carousel.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json --plan-only --json
python tools/produce_carousel.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json --output-dir .workspace/archives/carrossel --json
```

A entrega traz JPEGs numerados (`01-capa.jpg`, …), `carousel.zip` na mesma ordem e `carousel-manifest.json` (id, dimensões, caminhos, tamanhos, SHA-256). Remover um card e reexportar reflete a nova ordem no conjunto e no ZIP; uma falha preserva a última entrega válida.

### Motion (contorno animado)

A aba **Motion** permite configurar contorno animado por cena sem zoom (`MotionPlan` v1) reaproveitando o vídeo e as mídias do trabalho ativo, com prévia visual no canvas e troca de cenas preservada. Caminho mais curto:

```bash
python tools/make_agenda_media.py --output .workspace/tmp/motion-demo/assets/marca-salao/agenda.png
python tools/video_studio.py --port 8765   # aba Motion: selecionar cena, marcar região, salvar/exportar
# ou pela CLI:
python tools/produce_video.py --input tools/produce/examples/marca-salao-motion.video-request.json --motion-plan tools/produce/examples/marca-salao-motion.motion-plan.json --output-dir .workspace/archives/motion --json
```

O plano (`MotionPlan v1`) define região relativa, cor, espessura e intervalo por cena (`effects[]`); a prévia (`--plan-only`) resolve os tempos absolutos sem FFmpeg. O contorno é aplicado antes dos títulos/legenda, com entrada/saída suaves; o MP4 sai sem áudio, com SRT e narração. O plano canônico vai para o manifesto com hash. **Nesta rodada o Motion local está disponível apenas em 9:16**: o seletor do painel exclui os demais formatos e explica o recorte; enviar um `MotionPlan` a um destino horizontal falha somente naquele perfil (`MOTION_LOCAL_UNSUPPORTED_GEOMETRY`), preservando as entregas válidas dos demais.

## Workflow
Ver `WORKFLOW.md` para passo a passo completo e `AGENTS.md` para as regras do projeto.

## Contribuição
1. Adicione artes nas pastas correspondentes
2. Atualize legendas em `04-legendas/`
3. Commit + push

## Releases
Use GitHub Releases para distribuir pacotes de vídeo completos.

## Hermes e Postiz

[Documentação do Hermes](docs/hermes/README.md): prompts separados para Marca Salão e Multitrack Hub, conexão validada no Servidor02 e preparação de rascunhos com publicação somente após autorização específica.
