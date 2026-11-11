# R001 — Catálogo de formatos sociais (Instagram, Facebook, YouTube)

- **Requisito:** R001, pacote "Prompts R001 — Formatos de Instagram, Facebook e YouTube", fornecido pelo titular em 07/11/2026.
- **Etapa atual:** R001-05 concluída em 2026-11-07 (resolução das pendências de fonte: **17** regras oficiais promovidas com URL, `accessedOn` em UTC e citação literal; registro de pendências de **10 → 4**; revisões de perfil e os cinco exemplos re-geridos). Este é o **último checkpoint** da sequência (§13): o que existe adiante está em §15 (renderizador, exportação, publicação) e depende de decisão do titular, não de uma R001-06 planejada aqui.
- **Branch de trabalho:** `codex/catalogo-formatos-sociais` — **sem upstream local**, como corrigido na R001-02, e publicada em `origin` como ramo de mesmo nome pelo refspec explícito (`git push origin codex/catalogo-formatos-sociais`), sem escrever `git config`.
- **Base:** `origin/main = 0c97c2a4918e425a9d405dfb9ba0952e0212d181` (revalidado em 2026-11-07T01:57Z).
- **HEAD desta etapa:** `e1caf5e` (os cinco exemplos re-geridos) fecha sobre `9a977c7` (as regras promovidas, o vínculo nos perfis e os testes que as fixam), que por sua vez fecha sobre `d7dd931`/`8562cc3` (checkpoint R001-04), `29e3955` (exemplos que executam), `73d5a6b` (as duas CLIs e seus testes de processo), `9521de6` (escopo das regras como lista de contextos), `947b006` (checkpoint R001-03), `c704b30` (OutputPlan canônico), `3af7859` (checkpoint R001-02), `195e7e3` (catálogo), `fe9d8d7` (desenho corrigido), `32138bd`/`55bfc0c`. O commit de documentação que traz esta linha — README e este documento — vem **depois** de `e1caf5e` e não altera nenhuma das medidas abaixo. Nada foi enviado para `main`, que segue `0c97c2a` no clone e em `origin`; a branch foi **publicada** em `origin` a pedido do titular, já depois deste checkpoint e dos commits de documentação, sem PR aberto e sem upstream local. `git diff --stat 0c97c2a..e1caf5e` dá **34 arquivos, 7486 inserções e 11 remoções**; a etapa R001-05 até `e1caf5e` (`git diff --stat d7dd931..e1caf5e`) são **12 arquivos, 707 inserções e 146 remoções**. Os dois números são medidos **entre commits existentes**, por isso continuam válidos depois do commit de documentação que fecha a etapa.
- **Referências revalidadas:** PR #6 integrada em `main` (mesclada 2026-11-06T22:04:07Z); PR #7 **aberta** em `8eb11d4`; PR #1 aberta. Nenhum trabalho já integrado foi reaplicado.
- **Direção aprovada pelo titular:** rede → publicação → mídia → perfil técnico. Este documento não reabre essa decisão; resolve e registra apenas escolhas pequenas dentro dela.

## 1. O que existe hoje (capacidade observada)

Tudo desta seção foi lido no repositório nesta base. "Observado" ≠ "oficialmente exigido" ≠ "capaz de exportar".

### 1.1 Contratos do núcleo

| Fato | Evidência |
| --- | --- |
| `ProjectManifest.outputProfiles` é `string[]` — kebab-case, não vazio, sem duplicatas, **opaco ao núcleo**, sem geometria | `platform/src/project-contract.ts:52-53`; `platform/schemas/project.schema.json:85-93`; `platform/src/validate-project.ts:111-137` |
| `Composition.format` = `{ profile, width, height, fps }`, `additionalProperties: false`, fps inteiro 1–120 | `platform/src/composition-contract.ts:32-33` e `:59-66`; `platform/schemas/composition.schema.json` (`format`) |
| Regra entre documentos: `format.profile` precisa existir em `project.outputProfiles` | `platform/src/validate-composition.ts:779-785`, código `COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED` |
| Perfis nos exemplos oficiais hoje: `vertical-social` e `square-social` | `platform/examples/projects/marca-salao.project.json:15-17` (`["vertical-social"]`); `platform/examples/projects/fixture-project.project.json:15-17` (`["square-social"]`) |
| Geometria dos exemplos: `vertical-social` = 1080×1920 @30; `square-social` = 1080×1080 @24 | `platform/examples/compositions/marca-salao-pilot.composition.json:7-11`; `platform/examples/compositions/fixture-project-pilot.composition.json:7-11` |
| CLIs existentes: `content:validate-project` e `content:validate-composition` (exit 0/1/2, stdout só resultado, stderr operacional) | `platform/package.json` (`scripts`); `platform/src/validate-composition-cli.ts:7-13`, `:91-131` |
| Convenção de relatório determinístico: `valid`, `errors`, `warnings`, `summary` + campos ecoados; sem timestamp, sem caminho absoluto, sem ID aleatório, ordem fixa, `null` em overflow | `platform/src/validation-report.ts:9-83` |
| Ambiente: TypeScript ESM/NodeNext, `strict`, `verbatimModuleSyntax`, `erasableSyntaxOnly`, `noUncheckedIndexedAccess`, `noEmitOnError`; include `src/**/*.ts` e `tests/**/*.ts` | `platform/tsconfig.json` |
| Zero dependências de runtime; dev apenas `@types/node`, `ajv`, `typescript`; `engines.node = ">=22 <25"` | `platform/package.json`; guarda em `platform/tests/build-portability.test.ts:100-102` |

### 1.2 Geometria e seletores fora do núcleo

| Fato | Evidência |
| --- | --- |
| ComfyUI Marca Salão tem **três geometrias de arte**: `quadrado` 1080×1080, `vertical` 1080×1350, `stories` 1080×1920 | `marcas/marcasalao/comfyui/custom_nodes/servidor02_gemini/brand.py:14` (`FORMATS`) |
| Proporções correspondentes `1:1`, `4:5`, `9:16`; cliente aceita só esses três ratios e `1K`/`2K` | `.../artwork.py:11` (`RATIOS`); `.../client.py:25` |
| O seletor é `(rede, formato)` — `rede ∈ {facebook, instagram, compartilhado}` × `formato ∈ {quadrado, vertical, stories}`, seis pares obrigatórios | `.../__init__.py:138-139` e `:161` |
| Mesmo trio duplicado em outro lugar do fluxo de exportação | `marcas/marcasalao/comfyui/marcasalao_export.py:47` (`sizes`) e `:132-133` (`--square-art`, `--artworks`) |
| Multitrack Hub fixa quadrado 1080×1080 | `marcas/multitrackhub/comfyui/custom_nodes/servidor02_gemini/brand.py:60`; `marcas/multitrackhub/comfyui/multitrackhub_export.py:47` |
| Templates HyperFrames: `story_reel_vertical` 1080×1920 (`data-duration="8"`); `youtube_horizontal` 1920×1080 (`data-duration="10"`); `reel_link_overlay` 1080×1920, `fps: 30`, `duration: 27` | `templates/story_reel_vertical/index.html:5,165-167`; `templates/youtube_horizontal/index.html:5,200-201`; `templates/reel_link_overlay/hyperframes.json:5-8` |
| Os `meta.json` dos templates só têm `id`/`name`/`createdAt` — **não** guardam geometria | `templates/story_reel_vertical/meta.json`; `templates/youtube_horizontal/meta.json` |
| Ferramentas de vídeo: padrão 1080×1920 @30, `libx264`, também aceita 1920×1080; overlay `webm` (VP9) | `tools/build_video.py:30`, `:73`, `:80`, `:94`; `tools/edit_link_reel.py:3`, `:41`, `:57` |
| Fluxos de produção citam 1080×1920 @30 MP4 e PNG 1080×1920 | `WORKFLOW.md:40`, `:52`; `02-reels-shorts/README.md:3`, `:18`; `01-insta-stories/EDITAR_CAPCUT.md:17-19` |
| Política de marca hoje aprovada: **uma arte quadrada compartilhada** entre Facebook e Instagram; Stories são "outro formato" e pedem autorização; `story_requires_separate_request: True` | `AGENTS.md:52-54` (arte quadrada compartilhada) e `:39` (Stories pedem autorização); `.../brand.py:253-254`; `marcas/marcasalao/comfyui/README.md:3` |
| **Catálogo concorrente identificado:** a tríade `FORMATS` + `RATIOS` + `sizes` duplicada entre marca-salão e multitrack, mais `hyperframes.json` dos templates. A R001 é a proposta de fonte única; nenhuma dessas é consumida por `platform/` hoje | itens acima |
| 720×1280 como default interno: **não encontrado no repo** (só aparece como *mínimo* oficial no compartilhamento de Stories por app, e em docs de vendors dentro de `.agents/skills/**`, fora de escopo) | §2.2; busca em `templates/`, `tools/`, `marcas/`, `platform/` |

### 1.3 Vínculo com geradores e templates (estado real)

- **Nada em `platform/` gera mídia.** O núcleo lê JSON, valida e imprime relatório (`validate-*-cli.ts:60-73`).
- Imagem: o ComfyUI do Marca Salão **produz** as três geometrias, exportando **PNG** (`marcasalao_export.py:47`, `WORKFLOW.md:40`). A publicação de imagem do Instagram por API aceita **somente JPEG** (`S-IG-API`). Isso é uma **verificação pendente entre formato produzido e rota de publicação pretendida** — não prova falha no fluxo atual de Postiz (que publica por outros caminhos, não certificados aqui) nem autoriza conversão ou mudança de produção nesta R001.
- Vídeo: os templates cobrem **canvas** 1080×1920 e 1920×1080, e `tools/build_video.py` exporta H.264. Nada disso está ligado ao núcleo: `Composition.renderer.adapter` é string livre (exemplos usam `hyperframes`), sem verificação de capacidade. **`renderer.adapter` não deve ser marcado como pronto porque o canvas coincide.**
- YouTube: nenhuma enumeração de YouTube em código no repo; aparece em docs e na pasta `03-youtube-pdf/` (`WORKFLOW.md:64-65`). Portanto, um perfil social do YouTube é, hoje, **dado de catálogo sem gerador dedicado mapeado**.
- IDs de canal do Postiz estão *hardcoded* por marca (`.../brand.py:15`) — o núcleo não pode e não deve conhecê-los.

### 1.4 Onde `docs/contexto/` está

`docs/contexto/` **não existe nesta base**; existe apenas na PR #7 aberta (`origin/codex/atualiza-contexto-projeto` = `8eb11d4`): `README.md`, `ESTADO-ATUAL.md`, `PROXIMOS-PASSOS.md`, `HANDOFF.md`. Foi consultado como referência, não integrado. A PR #7 **não** contém registro de R001 (`R001` não ocorre em `docs/contexto/**`), então o requisito vive só no pacote do titular. Convenção lida lá e adotada aqui: `ESTADO-ATUAL.md` concentra fatos que mudam; os demais apontam para ele em vez de copiar hashes e contagens.

## 2. Fontes oficiais e regras verificadas

Consultadas em navegador real (páginas do Google Support entregam só o shell JS ao leitor simples) em **2026-11-07T01:58Z–02:00Z UTC** (06/11/2026 22:58–23:00 Brasília) e, na revalidação das pendências (R001-05), em **18:21Z**, **19:11Z**, **19:19Z** e **19:24Z UTC** do mesmo dia. Uma fonte é evidência para o que está escrito nela, naquele contexto — não para todas as regras de uma rede.

| Fonte | URL | O que a página diz |
| --- | --- | --- |
| `S-YT-CLASS` | https://support.google.com/youtube/answer/15424877?hl=pt-BR | "Como criar Shorts com até três minutos": Shorts **até 3 minutos**; qualificação automática por **proporção quadrada ou vertical** + duração ≤ 3 min (canais padrão: envios após 15/10/2024; canais oficiais de artistas: após 08/12/2025); Shorts **> 1 min** com reivindicação ativa do Content ID são bloqueados globalmente, sem recomendação e sem monetização; "Não há mudanças nas limitações para Shorts com menos de um minuto". |
| `S-YT-UPLOAD` | https://support.google.com/youtube/answer/12779649?hl=pt-BR | "Enviar vídeos ao YouTube Shorts": "de até 3 minutos" e "com uma proporção quadrada ou vertical". **Nenhuma resolução mínima declarada.** |
| `S-YT-ENCODE` | https://support.google.com/youtube/answer/1722171?hl=pt-BR | "Configurações **recomendadas** de codificação de envio". Abre com: "Estes recursos estão disponíveis apenas para parceiros que usam o Gerenciador de conteúdo do YouTube Studio." Contêiner MP4; áudio AAC-LC, Opus ou Eclipsa Audio; vídeo H.264; frame rate: "O conteúdo **precisa** ser codificado e enviado no mesmo frame rate em que foi gravado", comuns 24/25/30/48/50/60 (outros aceitos), remover entrelaçamento; "A proporção padrão para o YouTube em computadores é 16:9" e o player se adapta a vertical/quadrado; SDR BT.709. Não menciona Shorts. |
| `S-IG-API` | https://developers.facebook.com/docs/instagram-platform/content-publishing/ (redireciona para `/documentation/instagram-platform/content-publishing`) | "O **único formato de imagem compatível é o JPEG**. Não há compatibilidade com formatos derivados de JPEG, como MPO e JPS."; carrosséis "podem ter **no máximo 20** imagens, vídeos ou uma combinação dos dois"; "Todas as imagens do carrossel são cortadas com base na primeira escolhida. A **taxa de proporção padrão é de 1:1**."; Reels = contêiner de vídeo com `media_type=REELS`; recomenda consultar status do contêiner 1×/min por no máximo 5 min. **Sem números de resolução, peso ou duração de vídeo.** |
| `S-IG-MEDIA` | https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media | Referência de campos do objeto de mídia (Graph `v27.0`). **Sem especificação de geometria, formato ou duração.** Registrada como "sem evidência numérica". |
| `S-IG-STORY` | https://developers.facebook.com/documentation/instagram-platform/sharing-to-stories | "Compartilhamento no Stories" = fluxo pelo **app** (intent Android / `UIImage` iOS), **não** publicação por API. Para o ativo de fundo: "formato compatível (JPG, PNG). **Dimensões mínimas 720 x 1.280**. As proporções de imagem **recomendadas são 9:16 ou 9:18**." Para figurinha: "Dimensões recomendadas: 640 x 480." Página autodeclarada traduzida por IA. |

### 2.0.1 Segunda leva (R001-05): as fontes que certificaram as pendências

Toda citação abaixo foi lida na **versão em inglês** (`?hl=en` / `?locale=en_US`). As variantes pt-BR da Meta e do Google se autodeclaram tradução automática, e uma delas traduz literalmente "3 to 90 seconds" por "3 a 9 segundos" — defeito real, registrado em §2.2. Onde a URL sem locale responde 302 para login (caso do Help Center), o texto foi lido no navegador com o locale explícito. `accessedOn` no catálogo é o horário UTC da consulta desta leva, não uma data genérica.

| Fonte | URL (locale) | Consulta | Citação literal do que a página diz | O que respondeu |
| --- | --- | --- | --- | --- |
| `S-IG-USERMEDIA` | https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media?locale=en_US | 2026-11-07T19:11Z | "Aspect ratio: Must be within a 4:5 to 1.91:1 range · Minimum width: 320 (will be scaled up to the minimum if necessary) · Maximum width: 1440 (will be scaled down to the maximum if necessary) · Height: Varies, depending on width and aspect ratio" / "Format: JPEG · File size: 8 MB maximum. · Aspect ratio: We recommended 9:16 to avoid cropping or blank space" / "Duration: 60 seconds maximum, 3 seconds minimum · File size: 100MB maximum · Container: MOV or MP4 (MPEG-4 Part 14), no edit lists, moov atom at the front of the file." / "Duration: 15 mins maximum, 3 seconds minimum · File size: 300MB maximum · Video bitrate: VBR, 25Mbps maximum · Container: MOV or MP4 (…)" | certifica **`R-IG-06`** (faixa de proporção e largura de imagem de feed), **`R-IG-07`** (JPEG também em Stories por API — resposta direta a `P-IG-04`/`P-IG-05`), **`R-IG-08`** (teto de 60 s de Story de vídeo) e **`R-IG-09`** (teto de 15 min de Reel). Blocos "Image Specifications", "Story Image Specifications", "Story Video Specifications" e "Reel Specifications" da referência Graph v27.0 |
| `S-IG-HELP` | https://help.instagram.com/1631821640426723/?locale=en_US | 2026-11-07T19:11Z | "aspect ratio is between 1.91:1 and 3:4 (a width of 1080 pixels with a height between 566 and 1440 pixels)" | certifica **`R-IG-10`** como **recomendação de app** (`in-app`, sempre `informational`). A abertura sem locale respondeu 302 para login |
| `S-FB-PHOTOS` | https://developers.facebook.com/docs/graph-api/reference/page/photos/ | 2026-11-07T19:19Z | "File type: .jpeg, .bmp, .png, .gif, .tiff · File size: Files can not exceed 10MB. For .png files, we recommend not exceeding 1MB or the image may appear pixelated." | certifica **`R-FB-01`** (foto de Página por API) e **refuta por fonte própria** a hipótese de `P-FB-02`: o Facebook aceita cinco extensões, então a regra JPEG do Instagram **não** migra. Não declara dimensão nem proporção de foto → continua `P-FB-01` |
| `S-FB-STORIES` | https://developers.facebook.com/documentation/video-api/page-stories-api | 2026-11-07T19:19Z | "File type: .jpeg, .bmp, .png, .gif, .tiff · Files can not exceed 10MB." / "A video story can not exceed 60 seconds" / "Resolution: 1080 x 1920 pixels (recommended). Minimum is 540 x 960 pixels · Aspect Ratio: 9 x 16" / "Frame Rate: 24 to 60 frames per second" | certifica **`R-FB-02`**, **`R-FB-03`**, **`R-FB-04`** e **`R-FB-05`**. Página atualizada em 30/07/2026. Contradição interna ("Duration: 3 to 90 seconds." na tabela × "can not exceed 60 seconds" em Limitations) registrada em §2.2, não apagada |
| `S-FB-REELS` | https://developers.facebook.com/documentation/video-api/guides/reels-publishing | 2026-11-07T19:19Z | "Duration: 3 to 90 seconds. A reel published as a story on a Facebook Page can not exceed 60 seconds." / "Resolution: 1080 x 1920 pixels (recommended). Minimum is 540 x 960 pixels" / "Aspect Ratio: 9 x 16" / "File Type: .mp4 (recommended)" | certifica **`R-FB-06`**, **`R-FB-07`**, **`R-FB-08`** e **`R-FB-09`**. Escopo da página: "You can only publish Reels to Facebook Pages". Sem limite de bytes de vídeo → `P-FB-03` |
| `S-FB-VIDREF` | https://developers.facebook.com/documentation/video-api/reference | 2026-11-07T19:19Z | "Aspect Ratio: 9x16, 16x9" | é o objeto de vídeo de Página, **não** o Reel. Duas relações diferentes na mesma família de páginas é exatamente o motivo de **`R-FB-08` não ter `value`**: fechar uma lista afirmaria exclusividade que a fonte não declara |
| `S-YT-LONG` | https://support.google.com/youtube/answer/71673?hl=en | 2026-11-07T19:24Z | "By default, you can upload videos that are up to 15 minutes long. Verified accounts can upload videos longer than 15 minutes." / "The maximum file size you can upload is 256 GB or 12 hours, whichever is less." | certifica **`R-YT-05`** e **`R-YT-06`** (fecha `P-YT-01`). As abas Computer e Android da mesma resposta repetem os números, então o escopo certificado é `in-app` + `studio-upload`. Nenhum dos dois vira `value` |
| `S-YT-INSERT` | https://developers.google.com/youtube/data/reference/rest/v3/videos/insert?hl=en | 2026-11-07T19:24Z | "Maximum file size: 256GB. Accepted Media MIME types: video/*, application/octet-stream" | certifica **`R-YT-07`** (`api-publishing`). O caminho curto `/youtube/v3/docs/videos/insert` redireciona para esta URL; a citação foi tomada na URL final, em `hl=en` |
| `S-YT-QUOTA` | https://developers.google.com/youtube/data/determine_quota_cost | 2026-11-07T19:24Z | "The search.list and videos.insert methods have their own quota buckets. Each of these methods has a default daily limit of 100 per day. The quota cost is 1 per call." | vira **`PN-YT-02`** (nota de política, fora de `RuleKind`) e fecha `P-YT-02`. O histórico de revisões registra a mudança do custo de upload "from approximately 1600 units to approximately 100 units" (2025-12-04) e a quota granular de 2026-06-01 — qualquer número 1600 está obsoleto |
| `S-YT-API-GEN` | https://developers.google.com/youtube/v3/docs | 2026-11-07T19:24Z | landing da Data API; nenhuma especificação de contêiner própria de Short | **não certifica nada:** a lista geral de contêineres aceitos pelo YouTube não é própria de Short nem declara peso → `P-YT-03` |

### 2.1 Separação exigida: requisito × recomendação × default interno × contexto de uso

| ID | Enunciado | Classe | Contexto | Aplica a |
| --- | --- | --- | --- | --- |
| `R-IG-01` | JPEG é o único formato de imagem aceito | requisito | publicação por **API** | Instagram — **imagem de feed** (`applies`). A pergunta "e em Stories?" foi certificada pela segunda leva e **não** resolveu por extensão: virou regra própria, `R-IG-07` |
| `R-IG-02` | Carrossel ≤ 20 itens | requisito | API | **não existe no registro**: ID reservado a um destino fora do escopo desta fatia (§15, sem carrossel). A fonte `S-IG-API` certifica o número, mas promover regra sem perfil que a use seria catálogo morto |
| `R-IG-03` | Corte do carrossel segue a primeira imagem; proporção padrão 1:1 | requisito/comportamento | API | **não existe no registro**: mesmo caso de `R-IG-02` — reservado, certificado pela fonte, fora de escopo |
| `R-IG-04` | Stories por compartilhamento no app: mínimo 720×1280 | requisito | **app** | Instagram Stories — contexto do app, **informação**, nunca validação de plano |
| `R-IG-05` | Stories: proporções recomendadas 9:16 ou 9:18 | recomendação | app | Instagram Stories — **informação** |
| `R-IG-06` | Imagem por API: proporção **dentro da faixa** 4:5–1.91:1, largura mínima 320 e máxima 1440; altura varia | requisito | API | Instagram feed (imagem) — **documental**: `RuleValue` não expressa faixa, então o plano não avalia e avisa `NOT_ASSESSABLE`. Os presets 1080×1080 e 1080×1350 são **pontos internos da faixa**, não exigência da rede |
| `R-IG-07` | Imagem de Stories por API: JPEG, peso máximo 8 MB, proporção recomendada 9:16 | requisito | API | Instagram Stories (imagem) — `value` = `allowed-formats ['jpeg']`. Resolve a pendência que a R001-02 deixou: a exigência JPEG **alcança** Stories, declarada por tipo na referência de mídia; o "JPG, PNG" é do fluxo do app por SDK |
| `R-IG-08` | Vídeo de Stories por API: **máximo 60 s**, mínimo 3 s, 100 MB, contêiner MOV ou MP4 | requisito | API | Instagram Stories (vídeo) — `value` = `max-duration-seconds 60`. Só o teto vira valor: mínimo de duração, bytes e lista aberta de contêineres não têm expressão em `RuleValue` |
| `R-IG-09` | Reel por API: **máximo 15 min (900 s)**, mínimo 3 s, 300 MB, bitrate VBR até 25 Mbps, MOV ou MP4 | requisito | API | Instagram Reels — `value` = `max-duration-seconds 900`, verificável na soma declarada de cenas da Composition. A armadilha descartada: "3 to 90 s" é da Reels Publishing API, que se declara **"on a Facebook Page"** — número de Facebook, não de Instagram |
| `R-IG-10` | No app: foto com proporção entre 1.91:1 e 3:4 (largura 1080, altura 566–1440) | recomendação | **app** | Instagram feed (imagem) — **`informational`** em todo perfil: o caminho exportado pelo núcleo nunca é o app. O extremo do app (3:4) **diverge** do extremo da API (`R-IG-06`): duas regras precisamente para não apagar a divergência |
| `R-FB-01` | Foto de Página por API: `.jpeg, .bmp, .png, .gif, .tiff`, 10 MB máximo; para `.png`, recomendação de não passar de 1 MB | requisito | API | Facebook feed (imagem) — `value` = `allowed-formats` com as cinco extensões. **Refuta `P-FB-02` por fonte própria**: a regra JPEG do Instagram não se estende ao Facebook |
| `R-FB-02` | Foto de Story por API: as mesmas cinco extensões, 10 MB máximo | requisito | API | Facebook Stories (imagem) — `value` = `allowed-formats`. O peso de 10 MB fica no enunciado: bytes não têm forma em `RuleValue` |
| `R-FB-03` | Vídeo de Story por API: **não pode exceder 60 s** | requisito | API | Facebook Stories (vídeo) — `value` = `max-duration-seconds 60`. **Contradição interna da fonte registrada, não apagada:** a mesma página imprime "Duration: 3 to 90 seconds." na tabela e "can not exceed 60 seconds" em Limitations; nenhuma das duas autoriza um vídeo-story de 90 s, então promove-se o teto estrito |
| `R-FB-04` | Story de vídeo por API: resolução mínima **540×960**, 1080×1920 recomendados | requisito | API | Facebook Stories (vídeo) — `value` = `min-dimensions 540×960`, avaliado contra a geometria do plano. O preset 1080×1920 **cumpre**, então não gera aviso |
| `R-FB-05` | Frame rate de Story de vídeo por API: **24 a 60 fps** | requisito | API | Facebook Stories (vídeo) — **documental**: faixa, não valor. Fixar `fps: 30` como exigência aprovaria só o preset e reprovaria 25 e 60, que a página aceita |
| `R-FB-06` | Reel de Página por API: **3 a 90 s**; publicado como Story, o teto cai para 60 s | requisito | API | Facebook Reels — `value` = `max-duration-seconds 90` (o teto do caminho direto). Não confundir com `R-IG-09` (15 min) |
| `R-FB-07` | Reel de Página por API: resolução mínima **540×960**, 1080×1920 recomendados | requisito | API | Facebook Reels — `value` = `min-dimensions 540×960`. Os demais itens da tabela ("Chroma subsampling 4:2:0", "Closed GOP", "H.264/H.265/VP9/AV1", "Fixed frame rate", "Progressive scan") não têm forma em `RuleValue` e nenhum vira erro de plano |
| `R-FB-08` | Proporção declarada para Reel: 9×16; a referência de vídeo de Página aceita 9x16 **e** 16x9 | requisito | API | Facebook Reels — **documental**, sem lista fechada: duas relações certificadas em páginas de objetos distintos afirmariam exclusividade que a fonte não declara |
| `R-FB-09` | Contêiner recomendado para Reel de Página: `.mp4` | **recomendação** | API | Facebook Reels — `value` = `container 'mp4'`; a própria fonte marca como recomendação, então descumprimento gera aviso, nunca erro. A página não declara peso de vídeo → `P-FB-03` |
| `R-YT-01` | Shorts: até 3 minutos | requisito (classificação) | app / YouTube Studio | YouTube Shorts |
| `R-YT-02` | Shorts: proporção **quadrada ou vertical** (condição de orientação, não uma lista fechada de razões) | requisito (classificação) | app / YouTube Studio | YouTube Shorts |
| `PN-YT-01` | Shorts > 1 min com reivindicação ativa do Content ID → bloqueio global, sem recomendação e sem monetização | **nota de política** (`PolicyNote`, fora de `RuleKind`) | política de conteúdo | YouTube Shorts — só documental; o núcleo não sabe verificar reivindicação e não ganha verificador fictício |
| `R-YT-04` | MP4 / H.264 / AAC-LC-Opus-Eclipsa; enviar no mesmo fps da gravação; sem entrelaçado; 16:9 é o padrão em desktop; BT.709 para SDR | **recomendação**, seção restrita a parceiros do Gerenciador de conteúdo | upload | YouTube vídeo horizontal |
| `R-YT-05` | Envio ao YouTube: por padrão **até 15 min**; conta verificada envia mais longo | requisito | app / YouTube Studio | YouTube vídeo horizontal — **documental de propósito**: um `max-duration-seconds: 900` reprovaria o vídeo de conta verificada que a própria página permite. Condição de conta, não geometria |
| `R-YT-06` | Teto do arquivo: **256 GB ou 12 h**, o que vier primeiro | requisito | app / YouTube Studio | YouTube vídeo horizontal — **documental**: o teto é um mínimo entre bytes e duração, e nenhum dos dois tem forma em `RuleValue` |
| `R-YT-07` | `videos.insert` (Data API v3): 256 GB máximo; MIME aceitos `video/*` e `application/octet-stream` | requisito | **API** | YouTube vídeo horizontal — **documental**: `video/*` é uma classe, não uma lista de formatos; `allowed-formats` com "video/*" afirmaria um formato que a fonte não nomeia |
| `PN-YT-02` | Cota: `videos.insert` e `search.list` têm buckets próprios, limite padrão de **100 chamadas/dia**, custo 1 por chamada. O histórico registra a mudança "from approximately 1600 units to approximately 100 units" (2025-12-04) e a quota granular de 2026-06-01 — número 1600 está **obsoleto** | **nota de política** (`PolicyNote`) | cota de API | YouTube vídeo horizontal — o núcleo não autentica nem consulta quota; nada disso vira regra avaliável |
| `D-LOCAL-01…05` | quatro geometrias (1080×1080, 1080×1350, 1080×1920, 1920×1080) + fps 30 | **default interno** verificado por destino | — | presets de produção; no registro cada preset é uma entrada própria (`D-LOCAL-01`…`04`, `D-LOCAL-05` = fps), porque `RuleValue.geometry` é singular |

### 2.1.1 Estado de aplicação por regra (correção da revisão)

Uma regra não pode ser simultaneamente verificada e pendente para a mesma aplicação. Cada referência de perfil carrega **um** estado:

| Estado | Significado | Pode virar erro de plano? |
| --- | --- | --- |
| `applies` | a fonte cobre exatamente esta rede, esta publicação e **este contexto** | só se o contexto for o declarado na resolução |
| `informational` | a regra existe, mas pertence a outro contexto (ex. app) ou o núcleo não consegue verificá-la | **nunca** |
| `not-evaluated` | não há evidência de que a regra alcançaria esta publicação/contexto | **nunca**; vira pendência nomeada |

A resolução v1 **não seleciona rota de publicação por conta própria**. Quem quiser usar uma regra oficial como restrição precisa declarar o contexto explicitamente (R001-03); sem essa declaração, todas as regras oficiais aparecem como dado com sua origem e estado. Regras condicionais de outro contexto continuam visíveis como informação — é assim que `R-IG-04`/`R-IG-05` (app) convivem com um perfil cujo alvo é a API, sem virar exigência de API.

**O contexto precisa sobreviver à serialização (definição fechada na R001-03).** Condicionar a aplicação de regras a um contexto que existe só durante a chamada permite criar um plano com uma condição e relê-lo sem ela. Por isso `ruleContext?: RuleContext` entra **no OutputPlan** (§6.1), **nas opções de resolução** (§7), **no schema** (`enum` espelhando os valores de `types.ts`) e **no relatório** (§6.2, como valor ou `null`). Semântica fechada:

| Situação | Significado | Consequência no plano |
| --- | --- | --- |
| `ruleContext` **ausente** | contexto não informado | estruturalmente válido; regras oficiais condicionais viram `not-evaluated` no relatório, com aviso de que a validade **não** confirma exigência oficial |
| `ruleContext = null` ou valor fora do enum | entrada inválida | erro de contrato (`OUTPUT_PLAN_RULE_CONTEXT_INVALID`); ausência é representada pela **chave ausente**, nunca por `null` |
| contexto declarado e **igual** ao da regra | condição da fonte atendida | só `requirement` de regra com estado `applies` pode gerar erro oficial, e só quando o documento já traz dado suficiente para avaliá-la |
| contexto declarado e **diferente** do da regra | outra rota de publicação | a regra vira diagnóstico (`not-evaluated`/`informational`); nunca erro de outra rota |

`ProjectManifest` e `Composition` v1 **não** ganham campo novo: o contexto é do plano, não dos contratos antigos.

Consequências de desenho que decorrem dessa separação:

- **`R-YT-02` derruba uma crença comum:** a regra oficial de Shorts não exige 9:16 exclusiva nem resolução mínima; ela diz *quadrada ou vertical* + ≤ 3 min. O catálogo representa a **condição de orientação**, e 1080×1920 segue sendo escolha interna — as duas coisas não se confundem.
- **`R-IG-04`/`R-IG-05` não podem virar exigência de API** (§2.1, estado `informational`).
- **`R-YT-04` não é limite rígido** (página autodeclarada "recomendadas" e condicionada a parceiros de CMS). Nada de fps obrigatório 30 no YouTube a partir dessa fonte.
- **Regra de uma rede não migra para a outra — e a R001-05 provou por quê.** `R-IG-01` (JPEG) vale para a API do Instagram; a fonte própria do Facebook (`R-FB-01`) aceita **cinco** extensões. Se a regra tivesse sido copiada, o catálogo teria rejeitado PNG de Página por API com "evidência oficial". A hipótese que era `P-FB-02` foi **refutada por fonte**, não por conveniência.
- **Número parecido não é a mesma regra.** "3 a 90 segundos" aparece na Reels Publishing API de **Facebook**; a referência de mídia do Instagram diz Reel de **15 minutos**. A R001-05 quase promoveu o teto errado para a rede errada; a nota de `R-IG-09` registra a armadilha para a leitura não repetir o erro.
- **Faixa não vira valor único.** `R-IG-06` (proporção 4:5–1.91:1), `R-FB-05` (24–60 fps), `R-FB-08` (9×16 e 16×9), `R-YT-05`/`R-YT-06`/`R-YT-07` (bytes, 12 h, `video/*`) ficam **sem `value`** — o relatório diz `OUTPUT_PLAN_RULE_NOT_ASSESSABLE` em vez de fingir que verificou.
- **Divergência app × API é mantida, não reconciliada.** `R-IG-06` (API: até 1.91:1) e `R-IG-10` (app: até 3:4) dão números diferentes para a mesma família de destino; o catálogo conserva os dois, com o app sempre `informational`.

### 2.2 Pendências explícitas de fonte (sem número inventado)

Cada item abaixo fica **ausente** no catálogo, com ID nominal. Proibido representar "desconhecido" como `0`, `Infinity` ou número aproximado; proibido importar número de blog de terceiro como se fosse oficial.

### 2.2.1 O que a R001-05 promoveu (pendência → regra oficial)

Das **dez** pendências nomeadas na R001-02, **oito deixaram de existir** porque uma página de primeira mão respondeu (ou refutou, no caso de `P-FB-02`), e duas continuaram: `P-FB-01` **estreitada** — o que era "formatos, dimensões e durações" virou só "dimensão", porque o resto foi certificado — e `P-HELP-01` **revalidada sem número**, pois a página existe, abriu, e não declara regra nenhuma. Entraram **duas novas**, abertas pela própria leitura: certificar os formatos de foto abriu a pergunta "e o peso do vídeo?", que antes nem tinha nome. O registro foi de 10 → **4**. A contagem de regras promovidas (**17** `OfficialRule` + **1** `PolicyNote`) é maior que a de pendências extintas porque cada pendência antiga cobria vários números: `P-IG-01` e `P-IG-02` juntos nomeavam duração de Stories, duração de Reels, contêiner, peso e resolução.

| Pendência anterior | Virou | Fonte que certificou | O que exatamente respondeu |
| --- | --- | --- | --- |
| `P-IG-01` (duração máxima de Reels e Stories por API) | `R-IG-08` (60 s) e `R-IG-09` (900 s) | `S-IG-USERMEDIA` | blocos "Story Video Specifications" e "Reel Specifications" da referência de mídia, com `value` de `max-duration-seconds` |
| `P-IG-02` (contêiner, peso máximo e resolução de vídeo por API) | enunciados de `R-IG-08`/`R-IG-09` | `S-IG-USERMEDIA` | "Container: MOV or MP4 (…)", "File size: 100MB / 300MB maximum", "Video bitrate: VBR, 25Mbps maximum" — **todos documentais**: `RuleValue` não expressa peso, bitrate nem lista aberta de contêineres, então continuam exigindo inspeção de arquivo (`bytes`, `codec`) |
| `P-IG-03` (resolução máxima/mínima de imagem de feed) | `R-IG-06` (documental) e `R-IG-10` (app) | `S-IG-USERMEDIA`, `S-IG-HELP` | faixa de proporção 4:5–1.91:1 com largura 320–1440; o app declara 1.91:1–3:4. Nenhum par de pixels por proporção é declarado, e por isso a regra não tem `value` |
| `P-IG-04` + `P-IG-05` (o JPEG alcança Stories por API?) | `R-IG-07` | `S-IG-USERMEDIA` + corroborado por `S-IG-API` | "Format: JPEG" dentro de "Story Image Specifications", isto é, declarado **por tipo**. A armadilha registrada na nota da regra: "JPG, PNG" é do Sharing to Stories (SDK do app), não de publicação por API |
| `P-FB-01` (formatos, dimensões e durações do Facebook) — parcialmente | `R-FB-01`/`R-FB-02` (formatos), `R-FB-03`/`R-FB-06` (durações), `R-FB-04`/`R-FB-07` (mínimos de resolução), `R-FB-05` (frame rate), `R-FB-08` (proporção), `R-FB-09` (contêiner) | `S-FB-PHOTOS`, `S-FB-STORIES`, `S-FB-REELS` | o Facebook deixou de ter "zero regras verificadas". **A parte de dimensão de foto não foi certificada**: as páginas listam formatos e peso, mas nenhum mínimo, máximo ou proporção por destino → a pendência continua, estreitada (abaixo) |
| `P-FB-02` (a regra JPEG migra?) | **refutada**, não promovida | `S-FB-PHOTOS` | a fonte própria do Facebook aceita `.jpeg, .bmp, .png, .gif, .tiff`; a hipótese de extensão estava errada |
| `P-YT-01` (limite de duração/peso de vídeo longo) | `R-YT-05` e `R-YT-06` (documentais) | `S-YT-LONG` | 15 min padrão + conta verificada, e 256 GB **ou** 12 h, o que vier primeiro |
| `P-YT-02` (requisitos da Data API: cota, formato) | `R-YT-07` (documental) + `PN-YT-02` (nota de política) | `S-YT-INSERT`, `S-YT-QUOTA` | 256 GB e MIME `video/*` / `application/octet-stream`; cota de 100 chamadas/dia com custo 1, com o histórico de 1600 → 100 registrado como obsoleto |

### 2.2.2 O que continua pendente (quatro itens, texto literal do registro)

| ID | rede | contexto | Enunciado no catálogo | Por que continua |
| --- | --- | --- | --- | --- |
| `P-FB-01` | facebook | `null` | "Dimensões e proporção de foto de feed e de Story de imagem do Facebook: as páginas lidas listam formatos e peso, mas não afirmam mínimo, máximo nem proporção por destino; o número continua sem fonte certificada." | estreitada em vez de apagada: formatos e peso foram certificados (`R-FB-01`/`R-FB-02`), **dimensão não** |
| `P-FB-03` | facebook | `api-publishing` | "Peso máximo de arquivo de vídeo publicado por API no Facebook (Story e Reel de Página): as especificações de 'Video specifications' não declaram limite de bytes." | **nova**: as duas páginas de vídeo especificam duração, resolução, proporção, frame rate e codec, e omitem bytes |
| `P-YT-03` | youtube | `null` | "Contêiner e peso máximos específicos de Short: a página de Shorts certifica duração e proporção, e a lista geral de contêineres aceitos pelo YouTube não é própria de Short nem declara peso." | **nova**: a lista geral é do YouTube como produto, não do Short; tomar número geral por específico seria a migração de regra que a §2.1 proíbe |
| `P-HELP-01` | `null` | `in-app` | "Central de ajuda do app no facebook.com/help: landing genérica, sem regra numérica lida; regra de app não é exigência de exportação do núcleo." | acessada e **não** certificou; a contraparte do Instagram foi certificada nesta leva e virou `R-IG-10` |

O contexto de uma pendência é **singular** e só existe quando a própria fonte o delimita: `P-FB-03` e `P-HELP-01` têm contexto porque a pergunta foi feita a uma página de API/de app; `P-FB-01` e `P-YT-03` têm `null` porque a pergunta não tem rota única. Uma `PendingSourceRule` **não** tem `value`, `source` nem `evidence` — ausência tipada, nunca `null` no lugar do número.

### 2.2.3 Registro de acesso: o que falhou, o que ficou de fora e o que a tradução errava

- **`facebook.com/help` (Central de Ajuda do app):** landing genérica, sem número legível. Não virou regra porque não há enunciado para citar — o contrário de inventar um. Por isso continua como `P-HELP-01` e não como regra `applies`.
- **`help.instagram.com` sem locale:** respondeu **302 para login**. O mesmo conteúdo foi lido com `?locale=en_US` e virou `R-IG-10`. Acesso redirecionado é fato registrado, não motivo para descartar a regra que a página certifica.
- **`https://developers.facebook.com/docs/video-api/`** (citada na R001-02 como "não consultado com sucesso"): só aponta para a seção "Reference". Na R001-05 as três páginas específicas (`page-stories-api`, `guides/reels-publishing`, `graph-api/reference/page/photos/`) abriram e certificaram. A conclusão anterior estava limitada ao caminho tentado, não ao que a plataforma publica.
- **HTTP 429 da Meta:** persistem os dois fatos — o pacote do titular registrou 429 na abertura direta, a revisão de 06/11 reconfirmou indisponibilidade, e as duas levas desta execução (01:59Z e 19:11Z/19:19Z) conseguiram o conteúdo pelo navegador. **A rota de acesso é instável, não a informação.**
- **Defeito de tradução real:** a variante pt-BR da Stories API da Meta imprime **"3 a 9 segundos"** para "3 to 90 seconds". Nenhum número desta etapa foi lido de página autodeclarada traduzida; toda citação nova saiu da locale `en`. As regras anteriores (`R-IG-01`, `R-IG-04`, `R-IG-05`, `R-YT-01`, `R-YT-02`, `R-YT-04`) mantêm a citação com que foram certificadas, inclusive a `R-IG-01`, cuja fonte continua sendo a página de publicação que **se declara** traduzida — limitação registrada na própria `note`.
- **Contradição interna certificada (não resolvida em silêncio):** `S-FB-STORIES` imprime "Duration: 3 to 90 seconds." na tabela e "A video story can not exceed 60 seconds" em Limitations. Promoveu-se o teto estrito, porque nenhuma das duas autoriza 90 s em Story de vídeo; a divergência está na `note` de `R-FB-03`. Analogamente, `S-FB-REELS` ("Aspect Ratio: 9 x 16") × `S-FB-VIDREF` ("9x16, 16x9") deixou `R-FB-08` **sem `value`** em vez de escolher uma lista.
- **O que foi lido e deliberadamente não virou regra** (cada frase abaixo é literal, com a página onde foi lida):
  - cadência por conta — "Instagram accounts are limited to 100 API-published posts within a 24-hour moving period. Carousels count as a single post." (`S-IG-API`); "An Instagram account can only create 400 containers within a rolling 24 hour period" e "Containers expire after 24 hours" (`S-IG-USERMEDIA`); "Reels API is limited to 30 API-published posts within a 24-hour moving period." (`S-FB-REELS`). Nada disso é forma de arquivo nem geometria: o núcleo não autentica, não agenda e não conhece conta, então nenhuma dessas frases tem `RuleValue` possível. `PN-YT-02` é a única que entrou, como nota de política, porque a cota era justamente o núcleo de `P-YT-02`.
  - especificações de vídeo sem forma no contrato — "Maximum columns (horizontal pixels): 1920", "Required aspect ratio is between 0.1:1 and 10:1 but we recommend 9:16 to avoid cropping or blank space", "Audio bitrate: 128kbps" (`S-IG-USERMEDIA`, bloco "Story Video Specifications") e "Reels frame rate must be between 24 and 60 frames per second." (`S-FB-REELS`). **Faixa não é `RuleValue.fps`, que é singular**, e `aspect-ratios` é lista fechada, não intervalo: virar regra com `value` afirmaria exclusividade que a fonte não declara. Vivem nas `note` de `R-IG-08` e `R-FB-07`, certificadas e lidas, sem poder de erro.
  - pesos de arquivo — 8 MB (`R-IG-07`), 100 MB (`R-IG-08`), 300 MB (`R-IG-09`), 10 MB (`R-FB-01`/`R-FB-02`), "For .png files, we recommend not exceeding 1MB" (`R-FB-01`). Todos certificados, todos **documentais**: bytes só existem no arquivo, e o núcleo não inspeciona arquivo nesta fatia (§6.2.1, `bytes`).

**Registro de revalidação da R001-05** (o mecanismo prometido acima, executado): cada tentativa abaixo tem página, data/hora UTC e resultado. `18:21Z` — `S-YT-CLASS` (`answer/15424877`) e `S-YT-UPLOAD` (`answer/12779649`): **sucesso**, citações literais conferidas, escopo `in-app` + `studio-upload` confirmado pela própria frase — as duas frases que o registro guarda como `quote` são **"Você pode enviar Shorts de até três minutos pelo app YouTube e pelo YouTube Studio."** (`R-YT-01`) e **"de até 3 minutos e com uma proporção quadrada ou vertical"** (`R-YT-02`); a tabela de §2.0, escrita na R001-01, resume a mesma página em outras palavras, e onde as duas formulações divergem vale a `quote` do código, que é a cadeia consultada nesta hora. Convenção de elisão registrada: a `quote` de `PN-YT-01` — "Shorts com mais de um minuto ... reivindicação ativa do Content ID ... bloqueados globalmente" — é uma **emenda** de três trechos da mesma frase da página, com as reticências escritas; não é uma sentença contígua, e quem comparar com a página deve comparar trecho a trecho. `19:11Z` — `S-IG-USERMEDIA`: **sucesso** (4 blocos de especificação lidos); `S-IG-HELP`: **sucesso com locale explícito**, 302 para login sem locale; `S-IG-API` reaberta: **sucesso**, corrobora JPEG ao nível do documento. `19:19Z` — `S-FB-PHOTOS`, `S-FB-STORIES`, `S-FB-REELS`, `S-FB-VIDREF`: **sucesso**; a variante pt-BR de `S-FB-STORIES` reaberta de propósito e o **defeito de tradução confirmado**. `19:24Z` — `S-YT-LONG`, `S-YT-INSERT`, `S-YT-QUOTA`: **sucesso**; `facebook.com/help`: **landing genérica, sem número** (`P-HELP-01`); `developers.facebook.com/docs/video-api/`: **continua** só apontando para "Reference" (fato estável entre as duas execuções). Nenhuma entrada foi **rebaixada** por falha de acesso, e nenhuma regra anterior foi reescrita sem evidência nova — `R-IG-01`, `R-IG-04`, `R-IG-05`, `R-YT-01`, `R-YT-02`, `R-YT-04` mantêm a fonte com que foram certificadas.

**Disponibilidade da fonte e procedência da regra são estados distintos (definição fechada na R001-03).** Uma falha temporária de acesso não é evidência de que a regra mudou, então **não** rebaixa `requirement`/`recommendation` para `pending-source` nem apaga `source` (URL, título, data, citação) já registrado. O que se registra separadamente é a **tentativa de revalidação**: página, data/hora da tentativa e resultado (indisponível, 429, conteúdo alterado). Mudar uma regra exige **decisão baseada em evidência** — a nova fonte ou a contradição certificada — e revisor humano, não um erro de rede. Consequência prática e verificável: `resolveOutputPlan` e `validateOutputPlan` são funções puras que leem **somente** o catálogo versionado pelo código (`CATALOG_VERSION`), sem consultar rede nem disco; nenhuma entrada do registro é mutada por uma tentativa de revalidação. Enquanto não houver um mecanismo próprio de registro de revalidações, a tentativa fica documentada nesta seção, como o parágrafo acima já fazia — e continua vedado representar limite desconhecido como número aproximado.

## 3. Matriz de perfis (catálogo v1, estado medido na R001-05)

Doze perfis. `regras` usa os estados de aplicação de §2.1.1 (nada aqui é "exportação integrada"); `export` registra apenas o que existe hoje **fora** do núcleo. A matriz é o estado **medido** depois da R001-05: `rev` é a revisão do perfil no catálogo (`youtube-shorts` chegou a 3 — 1 → 2 pela correção de escopo da R001-04, 2 → 3 pela pendência estreitada em `P-YT-03`; os demais subiram 1 → 2 com as regras promovidas), e `notas` são `PolicyNote`, nunca regra avaliável.

| `profileId` | rev | rede | publicação | mídia | geometria interna | fps | regras (estado) | pendências | notas | export |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `instagram-feed-image-square` | 2 | instagram | feed | imagem | 1080×1080 (1:1) | — | `R-IG-01` `applies`, `R-IG-06` `applies` (documental), `R-IG-10` `informational` | — | — | gerador de arte existe; núcleo não exporta |
| `instagram-feed-image-portrait` | 2 | instagram | feed | imagem | 1080×1350 (4:5) | — | `R-IG-01` `applies`, `R-IG-06` `applies` (documental), `R-IG-10` `informational` | — | — | gerador existe; política aprovada hoje é a quadrada compartilhada |
| `instagram-stories-image` | 2 | instagram | stories | imagem | 1080×1920 (9:16) | — | `R-IG-07` `applies`, `R-IG-04` `informational`, `R-IG-05` `informational` | — | — | gerador existe; Stories pedem autorização por marca |
| `instagram-stories-video` | 2 | instagram | stories | vídeo | 1080×1920 (9:16) | 30 | `R-IG-08` `applies`, `R-IG-04`/`R-IG-05` `informational` (são de imagem, contexto app) | — | — | canvas `story_reel_vertical`; nada verificado |
| `instagram-reels-video` | 2 | instagram | reels | vídeo | 1080×1920 (9:16) | 30 | `R-IG-09` `applies` | — | — | canvas vertical + ferramenta de exportação |
| `facebook-feed-image-square` | 2 | facebook | feed | imagem | 1080×1080 (1:1) | — | `R-FB-01` `applies` | `P-FB-01` | — | gerador existe; arte quadrada compartilhada é o fluxo aprovado |
| `facebook-feed-image-portrait` | 2 | facebook | feed | imagem | 1080×1350 (4:5) | — | `R-FB-01` `applies` | `P-FB-01` | — | gerador existe |
| `facebook-stories-image` | 2 | facebook | stories | imagem | 1080×1920 (9:16) | — | `R-FB-02` `applies` | `P-FB-01` | — | gerador existe |
| `facebook-stories-video` | 2 | facebook | stories | vídeo | 1080×1920 (9:16) | 30 | `R-FB-03` `applies`, `R-FB-04` `applies`, `R-FB-05` `applies` (documental) | `P-FB-03` | — | canvas vertical; nada verificado |
| `facebook-reels-video` | 2 | facebook | reels | vídeo | 1080×1920 (9:16) | 30 | `R-FB-06` `applies`, `R-FB-07` `applies`, `R-FB-08` `applies` (documental), `R-FB-09` `applies` (recomendação) | `P-FB-03` | — | canvas + ferramenta de exportação; sem paridade com Instagram |
| `youtube-video-horizontal` | 2 | youtube | video | vídeo | 1920×1080 (16:9) | 30 | `R-YT-04` `applies` (recomendação de parceiros CMS), `R-YT-05`/`R-YT-06` `applies` (documentais, app+Studio), `R-YT-07` `applies` (documental, API) | — | `PN-YT-02` | canvas `youtube_horizontal`; sem gerador dedicado |
| `youtube-shorts` | 3 | youtube | shorts | vídeo | 1080×1920 (9:16) | 30 | `R-YT-01` `applies`, `R-YT-02` `applies` | `P-YT-03` | `PN-YT-01` | canvas vertical reaproveitado; classificação é automática |

Notas da matriz:

- **`P-IG-04`/`P-IG-05` deixaram de existir:** a referência de mídia declara JPEG **dentro do bloco de imagem de Story**, então `instagram-stories-image` passou a ter regra própria (`R-IG-07` `applies`) em vez de herdar `R-IG-01` com aplicação não avaliada. O `R-IG-01` continua só no feed — e a corroboração de nível de documento está na `note` da nova regra, não numa segunda exigência.
- **Facebook deixou de ter zero regras verificadas**, e o que impediria copiar do Instagram continua valendo: a fonte própria do Facebook **recusa** a hipótese de JPEG-exclusivo (`R-FB-01` aceita cinco extensões). O que não foi certificado — dimensão de foto e bytes de vídeo — segue nomeado (`P-FB-01`, `P-FB-03`).
- **`R-IG-06`, `R-FB-05`, `R-FB-08` e `R-YT-05…07` são `applies` sem `value`:** `applies` significa "a fonte cobre esta rede, publicação e contexto", não "o plano verifica". Com o contexto declarado, o relatório devolve `OUTPUT_PLAN_RULE_NOT_ASSESSABLE` — a regra está aplicada e nada foi aferido, que é o estado honesto para faixa, bytes e condição de conta.
- **`youtube-video-horizontal` não tem pendência de fonte:** o que falta ali não é ausência de número oficial, é ausência de **arquivo** (`bytes`, `codec`) e de capacidade de exportação. A cota virou nota de política (`PN-YT-02`) exatamente por não ser forma de mídia.
- `youtube-shorts` não declara resolução mínima: nenhuma fonte oficial certificada afixa número (§2.1, `R-YT-02`). A geometria 1080×1920 é escolha interna, e a condição oficial é de orientação.
- Reels de Instagram e de Facebook compartilham a **geometria**, não as **regras**: `R-IG-09` (900 s) e `R-FB-06` (90 s) são tetos diferentes da mesma família de páginas. É o caso mais caro de uma cópia entre redes.

## 4. Arquitetura e módulos

Camada de dados separada da camada de lógica, dentro de `platform/`, com zero dependências de runtime.

```
platform/src/
  output-profiles/
    types.ts                    # tipos e união discriminada imagem/vídeo        [R001-02]
    geometry.ts                 # constantes de geometria compartilhadas          [R001-02]
    rules.ts                    # registro de regras, notas de política e pendências [R001-02]
    catalog.ts                  # os 12 perfis + CATALOG_VERSION + listOutputProfiles
                                #   e findOutputProfile                            [R001-02]
  resolve-output-profile.ts     # seleção pura: allowlist do projeto × catálogo    [R001-03]
  output-plan-contract.ts       # tipos do OutputPlan v1                          [R001-03]
  validate-output-plan.ts       # estrutura + relações (projeto, catálogo, revisão) [R001-03]
  validate-composition-output.ts# compatibilidade Composition v1 × plano (delega a v1) [R001-03]
  output-profiles-cli.ts        # content:profiles                                 [R001-04]
  output-plan-cli.ts            # content:plan-output                              [R001-04]
platform/schemas/
  output-plan.schema.json       # espelho draft-07 fechado, oneOf imagem/vídeo     [R001-03]
platform/examples/
  projects/…social.project.json                                                    [R001-04]
  output-plans/*.output-plan.json                                                  [R001-04]
platform/tests/
  output-profiles-catalog.test.ts                                                  [R001-02]
  resolve-output-plan.test.ts / output-plan-validation.test.ts                     [R001-03]
  contracts/output-plan-schema.test.ts (ajv × core)                                [R001-03]
  output-cli.test.ts                                                               [R001-04]
```

`listOutputProfiles` e `findOutputProfile` moram em `catalog.ts`: são leitura do próprio catálogo, não resolução de plano. R001-02 **não** cria resolvedor, validador nem CLI.

Regras estruturais que a implementação deve manter:

1. **Núcleo independente de clientes.** O princípio está no `platform/README.md:12` ("Marca Salão será o primeiro consumidor da plataforma, não o núcleo da plataforma") e no `platform/README.md:17-19` (o núcleo não interpreta `brandTheme`, `locale`, `outputProfiles`). O `:12` foi recontado na R001-05: a lista de fatias ganhou a "Terceira fatia (R001)" na linha 10 e empurrou a citação de 11 para 12. Proibido em `platform/src` e `platform/schemas`: nome de marca, ID de canal, domínio comercial, tema editorial, caminho de projeto do consumidor. Catálogo e validadores podem nomear **redes** (Instagram, Facebook, YouTube) porque rede é o eixo do catálogo. **Permitido e necessário:** URL oficial de fonte (`RuleSource.url`) e evidência interna do repositório (`evidence: "arquivo:linha"`) — sem elas a procedência da regra se perde. A ligação catálogo ↔ geradores de arte, templates e publicadores fica em **documentos e testes**, não em dados do núcleo.
2. **Uma fonte só.** Nenhum segundo dicionário de formatos em CLI, exemplo ou teste. `build-portability.test.ts` e o teste de catálogo devem verificar que o que a CLI lista vem de `catalog.ts`.
3. **Sem condicionais por valor de marca/rede no comportamento genérico.** Não existe `if (network === 'youtube')` dentro do validador: as diferenças são dados do catálogo lidos pelo mesmo algoritmo.
4. **v1 intocada.** `ProjectManifest` e `Composition` mantêm estrutura, schemas, códigos e comportamento público atuais. O catálogo **reutiliza** os IDs de `outputProfiles` como allowlist; não migra, não reinterpreta e não exige catálogo para perfis opacos antigos (`vertical-social`, `square-social` seguem válidos e anonimamente aceitáveis).
5. **Um plano por seleção.** Não há expansão automática de "todas as variações". Um projeto pode permitir muitos perfis; cada pedido resolve um.

## 5. Forma do catálogo declarativo

Assinaturas de referência; os nomes exatos podem ser ajustados em R001-02, mas os **princípios** (união discriminada, proveniência, ausência em vez de zero) não.

```ts
// types.ts
export type OutputNetwork = 'instagram' | 'facebook' | 'youtube'
export type OutputPublication = 'feed' | 'stories' | 'reels' | 'shorts' | 'video'
export type OutputMediaKind = 'image' | 'video'
export type RuleContext = 'in-app' | 'api-publishing' | 'ads' | 'studio-upload'
export type RuleApplicationState = 'applies' | 'informational' | 'not-evaluated'
export type ExportState = 'preset-only' | 'canvas-template-mapped' | 'tool-export-observed'

export interface GeometryPreset {
    readonly width: number
    readonly height: number
    readonly aspectRatio: string        // forma "W:H", já reduzida
}

export interface RuleSource {
    readonly url: string                // https oficial
    readonly title: string
    readonly accessedOn: string         // "YYYY-MM-DDThh:mmZ" — data da consulta
    readonly quote: string              // trecho literal que sustenta a regra
    readonly note?: string              // ex.: tradução automática declarada pela página
}

export type RuleValue =
    | { readonly kind: 'allowed-formats'; readonly formats: readonly string[] }
    | { readonly kind: 'aspect-ratios'; readonly ratios: readonly string[] }
    | { readonly kind: 'orientation-any-of'; readonly orientations: readonly ('square' | 'portrait' | 'landscape')[] }
    | { readonly kind: 'min-dimensions'; readonly width: number; readonly height: number }
    | { readonly kind: 'max-count'; readonly count: number }
    | { readonly kind: 'max-duration-seconds'; readonly seconds: number }
    | { readonly kind: 'geometry'; readonly width: number; readonly height: number; readonly aspectRatio: string }
    | { readonly kind: 'fps'; readonly fps: number }
    | { readonly kind: 'container'; readonly container: 'mp4' | 'webm' }

/** Regra oficial: fonte obrigatória. `value` só existe quando a fonte certifica número/forma. */
export interface OfficialRule {
    readonly id: string                 // R-IG-01, R-YT-02, R-FB-04 ...
    readonly network: OutputNetwork
    readonly kind: 'requirement' | 'recommendation'
    readonly contexts: readonly RuleContext[]   // escopo: os contextos que a MESMA fonte certifica; nunca vazio
    readonly statement: string
    readonly value?: RuleValue                  // ausente = documental: R-IG-06, R-IG-10, R-FB-05, R-FB-08, R-YT-05, R-YT-06, R-YT-07
    readonly source: RuleSource
}

/** Default interno do repositório: evidência obrigatória, sem fonte externa. */
export interface InternalDefaultRule {
    readonly id: string                 // D-LOCAL-01 ...
    readonly network: null
    readonly kind: 'internal-default'
    readonly statement: string
    readonly value: RuleValue
    readonly evidence: string           // "arquivo:linha" ou seção deste documento
}

/** Pendência de fonte: sem `value`, sem `source`, sem `evidence` — ausência, não null. */
export interface PendingSourceRule {
    readonly id: string                 // P-FB-01, P-FB-03, P-YT-03, P-HELP-01 ...
    readonly network: OutputNetwork | null
    readonly kind: 'pending-source'
    readonly context: RuleContext | null
    readonly statement: string
}

export type CatalogRule = OfficialRule | InternalDefaultRule | PendingSourceRule

/** Informação de política que o núcleo não consegue verificar: `PN-YT-01` (Content ID) e `PN-YT-02` (cota de upload, que fecha `P-YT-02` na R001-05). `PN-*` é nota de política; `P-*` é pendência de fonte — IDs diferentes, estados diferentes. */
export interface PolicyNote {
    readonly id: string
    readonly network: OutputNetwork
    readonly statement: string
    readonly source: RuleSource
}

export interface ProfileRuleReference {
    readonly ruleId: string
    readonly state: RuleApplicationState
}

interface OutputProfileBase {
    readonly id: string                 // kebab-case: vira item de project.outputProfiles
    readonly name: string               // rótulo legível em português (dado, não mensagem)
    readonly revision: number           // >= 1
    readonly network: OutputNetwork
    readonly publication: OutputPublication
    readonly geometry: GeometryPreset
    readonly defaults: readonly string[]        // D-LOCAL-* que este perfil instancia
    readonly rules: readonly ProfileRuleReference[]
    readonly pendingIds: readonly string[]
    readonly noteIds: readonly string[]
    readonly exportState: ExportState
    /** Evidência interna da capacidade observada; nunca nomes "exportação integrada". */
    readonly exportEvidence: readonly string[]
}

export interface ImageOutputProfile extends OutputProfileBase {
    readonly mediaKind: 'image'
    /** Exclusões explícitas: fps/contêiner não são apenas ausentes, são proibidos no tipo. */
    readonly fps?: never
    readonly plannedContainer?: never
}

export interface VideoOutputProfile extends OutputProfileBase {
    readonly mediaKind: 'video'
    readonly fps: number
    readonly plannedContainer?: 'mp4' | 'webm'
    readonly plannedContainerEvidence?: string
}

export type OutputProfile = ImageOutputProfile | VideoOutputProfile

export const CATALOG_VERSION = '1'
```

Decisões embutidas nessa forma:

- **Imagem não recebe fps nem duração.** O ramo `image` proíbe os campos por tipo (`?: never`), então um fps de imagem é impossível por construção — e uma atribuição via variável intermediária é pega pelo compilador, não só pelo lint de objeto literal.
- **Uma representação para pendência.** `PendingSourceRule` não tem `value`, `source` nem `evidence`: ausência tipada, sem `null` e sem número. Proibido `0`/`Infinity` como "desconhecido".
- **Default interno é rastreável.** Cada `D-LOCAL-*` carrega `evidence` com `arquivo:linha` de caminho **não vinculado a marca**; onde a única evidência mora em diretório de marca (4:5), a evidência aponta para a seção §1.2 deste documento, que registra os caminhos completos.
- **Orientação permitida ≠ geometria do preset.** `R-YT-02` usa `orientation-any-of` (condição geral oficial); o perfil `youtube-shorts` usa `geometry` 1080×1920 como escolha interna. As duas camadas não se reduzem uma à outra.
- **Política fora de `RuleKind`.** `PN-YT-01` (Content ID) vive em `PolicyNote`: é informação, não classe de regra, e não ganha verificador fictício.
- **A união `RuleValue` não foi aumentada para acomodar a R001-05.** Peso de arquivo, bitrate, faixa de frame rate, faixa de proporção, duração mínima e lista aberta de contêineres continuam **sem forma**. Consequência medida no registro compilado: das **23** regras oficiais, **16** têm `value` e **7** são documentais (`R-IG-06`, `R-IG-10`, `R-FB-05`, `R-FB-08`, `R-YT-05`, `R-YT-06`, `R-YT-07`). Os outros cinco `value` do registro (21 no total) pertencem aos `internal-default` `D-LOCAL-01…05`, que são preset interno com procedência de caminho do repositório, não exigência de rede. Crescer a união para "resolver" uma faixa exigira um verificador que a fonte não sustenta — e `applies` sem `value` já é o estado correto: a regra alcança o perfil, o documento não traz o dado, o relatório diz `NOT_ASSESSABLE`.
- **`revision` é o número do perfil, não do catálogo.** `CATALOG_VERSION` continua `'1'` (é o contrato, não o conteúdo); as promovidas de regra mudaram **11 perfis de 1 → 2** e o `youtube-shorts` **2 → 3**. Artefato antigo com revisão ultrapassada é rejeitado (`OUTPUT_PLAN_PROFILE_REVISION_INVALID` / `..._MISMATCH`) em vez de ser lido como se ainda descrevesse o catálogo.

## 6. OutputPlan v1, relatórios e códigos

### 6.1 Estrutura do plano

```jsonc
{
  "schemaVersion": 1,
  "projectId": "fixture-project",
  "catalogVersion": "1",
  "profileId": "instagram-stories-image",
  "profileRevision": 2,
  "mediaKind": "image",
  "image": { "width": 1080, "height": 1920, "aspectRatio": "9:16" }
}
```

e, no ramo de vídeo, com o contexto declarado (§2.1.1):

```jsonc
{
  "schemaVersion": 1,
  "projectId": "fixture-project",
  "catalogVersion": "1",
  "profileId": "youtube-shorts",
  "profileRevision": 3,
  "mediaKind": "video",
  "ruleContext": "studio-upload",
  "video": { "width": 1080, "height": 1920, "aspectRatio": "9:16", "fps": 30 }
}
```

Ordem das chaves no JSON canônico: `schemaVersion`, `projectId`, `catalogVersion`, `profileId`, `profileRevision`, `mediaKind`, `ruleContext` (só quando informado), `image` **ou** `video`. Os limites **estruturais** — inteiros seguros positivos para dimensões e revisão, `fps` inteiro 1–120, IDs kebab-case, `aspectRatio` na forma `W:H`, `ruleContext` no enum de `types.ts` — são do contrato e moram em `output-plan-contract.ts`, espelhados no schema. A relação desses valores com os do catálogo é **semântica** e só o validador do core a decide (§6.4).

`ruleContext` é opcional: ausente significa "contexto não informado" (§2.1.1). Ele **não** altera `ProjectManifest` nem `Composition` v1.

Vínculos exigidos: projeto, `profileId`, `profileRevision`, `catalogVersion`, `mediaKind` e parâmetros resolvidos — nada além disso. O schema `output-plan.schema.json` é **fechado** (`additionalProperties: false` no topo e nos dois payloads) e usa `oneOf` discriminado por `mediaKind`, com `image`/`video` mutuamente exclusivos. A versão v1 **não** define `duration`: duração pertence à Composition/BeatPlan, e um plano de imagem não pode carregar duração fictícia. O plano também **não** certifica formato de arquivo: nenhum campo de contêiner/extensão existe no ramo `image`. Depois da R001-05 a **regra** de formato é conhecida (`R-IG-07`, `R-FB-01`, `R-FB-02`), mas o que o plano carrega é geometria declarada, não a forma inspecionada do arquivo (§1.3, §6.2.1 `media-file`/`image-format`) — `allowed-formats` só teria o que comparar contra um byte mágico que nada nesta fatia lê.

O plano **não** carrega regras nem pendências: ele é o resultado resolvido. Diagnóstico, `pendingIds` e o que ainda exige inspeção de arquivo vivem no relatório (§6.2). Assim um plano jamais pode afirmar ter certificado publicação.

### 6.2 Relatórios

Mesmas regras de determinismo de `validation-report.ts:1-83`: `valid`, `errors`, `warnings`, `summary`, ordem de emissão fixa, sem timestamp, sem caminho absoluto, sem ID aleatório, entrada não mutada.

```ts
export interface OutputPlanReport {
    valid: boolean
    errors: ValidationIssue[]
    warnings: ValidationIssue[]
    summary: string
    projectId: string | null
    profileId: string | null
    catalogVersion: string | null
    profileRevision: number | null
    mediaKind: OutputMediaKind | null
    /** Contexto declarado na resolução; null quando não informado — nunca "sem contexto" como string. */
    ruleContext: RuleContext | null
    geometry: { width: number; height: number; aspectRatio: string } | null
    fps: number | null                        // null em imagem: nunca 0, nunca inventado
    pendingRuleIds: readonly string[]         // pendências nominais do perfil
    requiresInspection: readonly string[]     // enum estável, em ordem fixa (§6.2.1)
}

export interface OutputCompatibilityReport {
    valid: boolean
    errors: ValidationIssue[]
    warnings: ValidationIssue[]
    summary: string
    compositionId: string | null
    profileId: string | null
    /** Mesma convenção do plano: valor declarado ou null quando ausente. */
    ruleContext: RuleContext | null
    /** Soma declarada das cenas; null quando ausente, malformada ou em overflow. Não é duração de arquivo. */
    totalDurationMs: number | null
    /** Erros da v1 reproduzidos quando a delegação falha, sem duplicar diagnóstico. */
    compositionReport: CompositionValidationReport | null
    /** Relatório do plano (causa da falha preservada quando o plano é rejeitado antes da comparação). */
    planReport: OutputPlanReport | null
}
```

Forma documentada de `compositionReport` e `planReport`: são os **relatórios completos** emitidos por `validateComposition` e `validateOutputPlan` na mesma chamada, embutidos sem resumo nem recorte. Eles só aparecem preenchidos quando há o que preservar: `compositionReport` é `null` se a delegação não rodou (plano inválido rejeitado antes), `planReport` é `null` quando o plano não foi lido como objeto. Um relatório embutido nunca é comparado com um plano — são tipos diferentes (§7).

#### 6.2.1 `requiresInspection` (enum estável, ordem fixa)

| Valor | Ramos | Por que continua necessidade |
| --- | --- | --- |
| `media-file` | imagem e vídeo | o núcleo não abre arquivo nenhum; existir ou não existir é fato externo |
| `image-format` | imagem | PNG × JPEG é verificação pendente entre formato produzido e rota pretendida (§1.3, §10.1); a regra oficial existe desde a R001-05 (`R-IG-07`, `R-FB-01`, `R-FB-02`), mas comparar exige abrir o arquivo — e nenhum probe roda aqui |
| `codec` | vídeo | H.264/VP9 e contêiner real dependem de probe |
| `bytes` | imagem e vídeo | o **peso continua sendo fato de arquivo**, não de plano: os tetos certificados (`R-IG-07` 8 MB, `R-IG-08` 100 MB, `R-IG-09` 300 MB, `R-FB-01`/`R-FB-02` 10 MB, `R-YT-06`/`R-YT-07` 256 GB) não têm `RuleValue` possível e nada aqui abre o arquivo. O que a R001-05 **não** conseguiu certificar tem nome: `P-FB-03` (bytes de vídeo do Facebook) e `P-YT-03` (contêiner/peso de Short) |
| `audio-streams` | vídeo | a política de entrega é sem áudio (AGENTS.md), mas **afirmar** que o arquivo não tem faixa exige probe; o núcleo não faz |
| `publication` | imagem e vídeo | o núcleo planeja, não publica |

Ordem emitida: `media-file`, `image-format` (imagem) ou `codec` (vídeo), `bytes`, `audio-streams` (vídeo), `publication`. Nada nessa lista é limite inventado: a ausência de número continua como ID nominal de §2.2, levada no relatório em `pendingRuleIds`.

### 6.3 Códigos de erro previstos

| Código | Quando |
| --- | --- |
| `OUTPUT_PROFILE_ID_INVALID` | `profileId` ausente, não-string, vazio ou fora de kebab-case (na resolução e no plano) |
| `OUTPUT_PROFILE_UNKNOWN` | `profileId` não existe no catálogo |
| `OUTPUT_PROFILE_NOT_ALLOWED` | existe no catálogo, ausente em `project.outputProfiles` |
| `OUTPUT_PROFILE_AMBIGUOUS_SELECTION` | filtros de rede/publicação/mídia que contradizem o perfil escolhido ou não casam com nenhum perfil do catálogo |
| `OUTPUT_PROFILE_FILTER_INVALID` | filtro fora dos valores de `types.ts` (rede, publicação ou mídia inválida) |
| `OUTPUT_PROJECT_INVALID` | manifesto inválido; delega ao validador de projeto, sem reimplementar |
| `OUTPUT_PLAN_MEDIA_FIELDS_MISMATCH` | payload ausente, dos dois lados, ou de outro `mediaKind` |
| `OUTPUT_PLAN_INVALID` | entrada do plano não é objeto JSON |
| `OUTPUT_PLAN_UNKNOWN_FIELD` | campo de topo ou de payload fora da superfície do contrato (`additionalProperties: false`) |
| `OUTPUT_PLAN_SCHEMA_VERSION_UNSUPPORTED` | `schemaVersion` diferente de `1` |
| `OUTPUT_PLAN_PROJECT_ID_INVALID` | `projectId` ausente ou fora de kebab-case |
| `OUTPUT_PLAN_MEDIA_KIND_INVALID` | `mediaKind` ausente ou fora de `image`/`video` |
| `OUTPUT_PLAN_DIMENSIONS_INVALID` | dimensão não-inteira, ≤ 0 ou acima de `Number.MAX_SAFE_INTEGER` |
| `OUTPUT_PLAN_ASPECT_RATIO_INVALID` | `aspectRatio` fora da forma `W:H` |
| `OUTPUT_PLAN_FPS_INVALID` | `fps` não-inteiro ou fora de 1–120 (limite **estrutural** do plano) |
| `OUTPUT_PLAN_RULE_CONTEXT_INVALID` | `ruleContext` presente como `null` ou fora do enum (§2.1.1) |
| `OUTPUT_PLAN_CATALOG_VERSION_UNKNOWN` | `catalogVersion` diferente da suportada |
| `OUTPUT_PLAN_PROFILE_REVISION_INVALID` | revisão não-inteira positiva **ou** incompatível com o catálogo atual (mensagens distintas, mesmo código) |
| `OUTPUT_PLAN_PROJECT_MISMATCH` | `projectId` do plano divergente do manifesto informado |
| `OUTPUT_PLAN_MEDIA_KIND_MISMATCH` | `mediaKind` do plano divergente do perfil no catálogo |
| `OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG` | `width`, `height` **ou** `aspectRatio` divergem do preset interno (o `path` distingue) |
| `OUTPUT_PLAN_FPS_NOT_IN_CATALOG` | `fps` divergente do preset do perfil |
| `OUTPUT_COMPAT_PROFILE_MISMATCH` | `composition.format.profile` diferente do `profileId` do plano |
| `OUTPUT_COMPAT_DIMENSIONS_MISMATCH` | `format.width`/`format.height` divergentes das dimensões do plano |
| `OUTPUT_COMPAT_FPS_MISMATCH` | `format.fps` divergente do `fps` do plano |
| `OUTPUT_COMPAT_IMAGE_NO_COMPOSITION` | compatibilidade pedida para plano de imagem (`fps` não é fabricado) |
| `OUTPUT_COMPAT_COMPOSITION_INVALID` | a v1 rejeitou a Composition antes da comparação (causa preservada em `compositionReport`) |
| `OUTPUT_COMPAT_PLAN_INVALID` | o plano foi rejeitado antes da comparação (causa preservada em `planReport`) |
| `OUTPUT_COMPAT_DURATION_EXCEEDED` | `requirement` de duração violado pela soma declarada, **com o contexto da fonte declarado** (§6.4) |
| `OUTPUT_PLAN_OFFICIAL_REQUIREMENT_VIOLATED` | `requirement` com estado `applies` violado por dado que **o próprio plano carrega** (geometria, orientação, proporção, mínimo, fps); o `path` e a mensagem nomeiam a regra e o contexto (§6.4) |
| `OUTPUT_PLAN_RULE_UNRESOLVED` | referência de perfil que não resolve no registro de regras — erro, nunca silêncio (§6.4) |
| `OUTPUT_PLAN_CONTEXT_NOT_DECLARED` | *aviso*: perfil tem regra oficial e o plano não informou contexto — a validade estrutural **não** confirma exigência oficial |
| `OUTPUT_PLAN_RULE_NOT_EVALUATED` | *aviso*: referência com estado `not-evaluated` |
| `OUTPUT_PLAN_RULE_INFORMATIONAL` | *aviso*: referência com estado `informational` (outra rota; nunca vira erro) |
| `OUTPUT_PLAN_RULE_NOT_APPLIED` | *aviso*: regra `applies` de contexto **diferente** do declarado |
| `OUTPUT_PLAN_RULE_NOT_ASSESSABLE` | *aviso*: contexto bate e a regra é `requirement`, mas o documento não traz dado para avaliá-la (duração é da Composition; formato é de arquivo) |
| `OUTPUT_PLAN_RECOMMENDATION_NOT_MET` | *aviso*: recomendação não atendida — jamais erro |

Violação de **preset interno** (`OUTPUT_PLAN_DIMENSIONS_NOT_IN_CATALOG`, `OUTPUT_PLAN_FPS_NOT_IN_CATALOG`) é diferente de violação de **requisito oficial** (`OUTPUT_PLAN_OFFICIAL_REQUIREMENT_VIOLATED`, `OUTPUT_COMPAT_DURATION_EXCEEDED`): os códigos são separados e as mensagens nomeam a origem (`internal default` vs `official rule @contexto`), para nunca elevar escolha nossa a exigência de rede.

### 6.4 Avaliação das regras do catálogo (algoritmo único)

Um único caminho de código — usado por `validateOutputPlan` e por `validateCompositionForOutputPlan`, sem `if` por nome de rede, ID de perfil ou marca — decide o que cada referência de perfil significa:

1. Resolver `ruleId` no registro (`findCatalogRule`); referência que não resolve é erro, não silêncio.
2. Separar por classe: `internal-default` alimenta apenas a comparação de preset; `pending-source` alimenta `pendingRuleIds`; `PolicyNote` é dado informativo e não entra na avaliação.
3. Estado `informational` ou `not-evaluated` → **aviso**, qualquer que seja o contexto.
4. Classe `recommendation` → no máximo **aviso** (`OUTPUT_PLAN_RECOMMENDATION_NOT_MET`), mesmo com contexto batendo.
5. Classe `requirement` com estado `applies`:
   - `ruleContext` ausente ou **fora do escopo** (`!rule.contexts.includes(contexto)`) → aviso (`OUTPUT_PLAN_CONTEXT_NOT_DECLARED` / `OUTPUT_PLAN_RULE_NOT_APPLIED`) e **nenhum** erro;
   - contexto declarado dentro do escopo → avaliar **somente se houver dado no documento**: `aspect-ratios`, `orientation-any-of` e `min-dimensions` se avaliam de geometria; `max-duration-seconds` só se avalia da soma declarada da Composition; `allowed-formats`, `container` e `max-count` dependem de arquivo ou de campo que o plano não tem → `OUTPUT_PLAN_RULE_NOT_ASSESSABLE`.
6. Erro oficial leva o código próprio da relação, o `path` do campo avaliado e a mensagem citando `official rule <id>` seguido do escopo (`@<contexto>` por item, na ordem declarada no catálogo).

Isso é o que mantém §2.1.1 executável sem inventar verificador: `R-IG-04` (720×1280, contexto app) nunca derruba um plano resolvido para `api-publishing`, e `R-YT-01` (180 s, escopo `in-app` + `studio-upload`) só vira erro quando o contexto declarado está no escopo **e** a Composition traz a soma das cenas — o mesmo `value` atende os dois caminhos, um por vez, conforme o que quem chama declara.

Os três comportamentos que a R001-05 tornou visíveis, medidos pela CLI (`platform/tests/output-clis-process.test.ts`):

- **`applies` documental não vira passe livre.** `facebook-reels-video --rule-context api-publishing` emite `OUTPUT_PLAN_RULE_NOT_ASSESSABLE` para `R-FB-06` (duração: o plano não tem), `R-FB-08` (proporção: sem `value`) e `R-FB-09` (contêiner: arquivo), e **nenhum aviso** para `R-FB-07` — porque `min-dimensions 540×960` se avalia da geometria do plano e o preset 1080×1920 a cumpre. Mesmo sinal, saída diferente: avaliação de verdade onde o dado existe.
- **Um teto certificado abre uma borda verificável.** `R-IG-09` (900 s) saiu de `P-IG-01`: `450000 + 450000 = 900000 ms` → exit **0**; `450000 + 450001 = 900001 ms` → exit **1**, stdout vazio, com `OUTPUT_COMPAT_DURATION_EXCEEDED`, "Declared scene total of 900001 ms exceeds 900 s" e a origem `"R-IG-09" @api-publishing`. A borda é inclusiva no teto, como a de `R-YT-01` em 180 s.
- **Sem contexto declarado, a regra nova aparece como o que é.** O plano de `instagram-reels-video` sem `--rule-context` continua **válido** e ganha `OUTPUT_PLAN_CONTEXT_NOT_DECLARED` nas camadas de plano e de compatibilidade, com `pendencias de fonte: (nenhuma)` no stderr — ausência de pendência não é certificado de publicação, e a mensagem diz que nada foi confirmado.

## 7. Funções puras (contrato entre etapas)

```ts
// catalog.ts — implementado em R001-02 (leitura do catálogo, sem resolução)
export interface OutputProfileFilter {
    network?: OutputNetwork
    publication?: OutputPublication
    mediaKind?: OutputMediaKind
}
export function listOutputProfiles(filter?: OutputProfileFilter): readonly OutputProfile[]
export function findOutputProfile(profileId: string): OutputProfile | null

// resolve-output-profile.ts — R001-03
export function projectAllowedProfiles(projectInput: unknown): {
    allowed: readonly string[]
    report: ProjectValidationReport
}

/** Opções de resolução: filtros de leitura do catálogo + contexto das regras (§2.1.1). */
export interface OutputPlanResolutionOptions {
    readonly network?: OutputNetwork
    readonly publication?: OutputPublication
    readonly mediaKind?: OutputMediaKind
    /** Ausente = contexto não informado. `null` ou valor fora do enum é entrada inválida. */
    readonly ruleContext?: RuleContext
}

/** O resolvedor devolve o plano canônico E o diagnóstico; nunca só o relatório. */
export interface OutputPlanResolution {
    readonly plan: OutputPlan | null      // nulo apenas quando há erro
    readonly report: OutputPlanReport
}
export function resolveOutputPlan(
    projectInput: unknown,
    profileIdInput: unknown,
    optionsInput?: OutputPlanResolutionOptions,
): OutputPlanResolution                   // nunca lança; erro vira relatório

// validate-output-plan.ts — R001-03 (relatório, sem plano)
export function validateOutputPlan(planInput: unknown, projectInput: unknown): OutputPlanReport

// validate-composition-output.ts — R001-03
export function validateCompositionForOutputPlan(
    compositionInput: unknown,
    projectInput: unknown,
    planInput: unknown,
): OutputCompatibilityReport              // delega validateComposition(composition, project) primeiro
```

**Round-trip obrigatório, com as assinaturas reais.** O caminho testado é `plan` → `JSON.stringify(plan, null, 2)` (chaves na ordem declarada em §6.1) → `JSON.parse` → `validateOutputPlan(objetoRelido, projeto)`. `validateOutputPlan` **devolve relatório, não plano** — exigir um segundo `plan` na volta seria pedir uma saída que a função não tem, e comparar um relatório com um plano seria comparar tipos diferentes. A relação entre os dois relatórios é definida assim:

- na **resolução bem-sucedida**, `validateOutputPlan(JSON.parse(JSON.stringify(resolution.plan)), projeto)` produz um relatório **profundamente igual** a `resolution.report` — os dois rodam o mesmo avaliador de regras (§6.4) sobre os mesmos dados;
- `resolution.plan` é não-nulo **somente** quando `resolution.report.valid === true`; erro devolve `plan: null` e diagnóstico no relatório;
- a CLI **não reconstrói** o plano a partir dos campos ecoados do relatório: relatório é diagnóstico, plano é artefato;
- `ruleContext`, `projectId`, `catalogVersion`, `profileId`, `profileRevision` e o payload precisam sobreviver ao JSON — um plano criado com contexto e relido sem ele é contrato quebrado, e há teste para os dois sentidos (com e sem contexto) mais a rejeição de plano adulterado.

Em R001-03 o round-trip é coberto em teste; a comparação do JSON com os exemplos versionados em `examples/output-plans/` pertence a R001-04, onde os exemplos existem.

Invariants que as funções devem manter: entrada nunca mutada (comparação por clone profundo nos testes); catálogo lido como `readonly`; nenhum acesso a rede, disco, `process.env` ou escrita de arquivo — as CLIs leem **apenas** os caminhos passados, como `validate-composition-cli.ts:60-73`; saída determinística byte a byte para a mesma entrada.

## 8. CLI e scripts npm (R001-04)

**Estado em R001-04:** as duas CLIs existem, rodam sobre o build compilado e são testadas **como processo** — filho real via `spawnSync(process.execPath, [cli, …])`, argv como **array** (nada de shell string), inclusive com caminhos contendo espaço. Os scripts seguem o padrão `npm run build --silent && node dist/src/<cli>.js` já usado pelas CLIs antigas, e o `--silent` do build interno não é cosmético: sem ele o npm imprime o cabeçalho do script no stdout e nenhum consumidor de JSON consegue parsear a saída. A exigência está escrita em teste (`platform/tests/build-portability.test.ts`).

```jsonc
"content:profiles":    "npm run build --silent && node dist/src/output-profiles-cli.js",
"content:plan-output": "npm run build --silent && node dist/src/output-plan-cli.js"
```

Todos os comandos abaixo **foram executados** de dentro de `platform/` (diretório de execução dos scripts npm — por isso os caminhos começam em `examples/`, não em `platform/examples/`), com Node **v22.23.2**:

```
npm run --silent content:profiles
npm run --silent content:profiles -- --network instagram --publication reels --media video
npm run --silent content:profiles -- --project examples/projects/marca-salao-social.project.json
npm run --silent content:profiles -- --project examples/projects/marca-salao-social.project.json --network youtube --json

npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json --profile youtube-shorts --json
npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json --profile youtube-shorts --rule-context studio-upload

# (A) compatibilidade POSITIVA: composition social com format.profile = instagram-reels-video
npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json \
                               --profile instagram-reels-video --composition examples/compositions/marca-salao-social-reel.composition.json --json

# (B) exemplo de INCOMPATIBILIDADE: a composição oficial antiga declara `vertical-social`, não o perfil do plano
npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json \
                               --profile instagram-reels-video --composition examples/compositions/marca-salao-pilot.composition.json

# (C) regras documentais em ação: contexto certificado pela página, sem pendência de formato
npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json \
                               --profile facebook-reels-video --rule-context api-publishing
```

Saída medida de (A) na R001-05, exit **0**. As **nove** primeiras linhas são o **stderr**; o bloco JSON é o stdout, na íntegra. A camada de plano agora fala, porque `instagram-reels-video` tem uma regra oficial aplicada (`R-IG-09`) e o documento não declarou contexto — saída que na R001-04 era silêncio:

```
Avisos (camada plano):
  OUTPUT_PLAN_CONTEXT_NOT_DECLARED @ruleContext: Rule "R-IG-09" (@api-publishing) cannot be assessed because the document declares no context; structural validity does not confirm an official requirement.
Avisos (camada composicao):
  COMPOSITION_RENDERER_UNDECIDED @renderer.adapter: renderer.adapter is "undecided": no renderer is adopted by this composition yet.
Avisos (camada compatibilidade):
  OUTPUT_PLAN_CONTEXT_NOT_DECLARED @ruleContext: Rule "R-IG-09" (@api-publishing) cannot be assessed because the document declares no context; structural validity does not confirm an official requirement.
pendencias de fonte: (nenhuma)
requer inspecao: media-file, codec, bytes, audio-streams, publication
compatibilidade: composicao "social-reel-example" compativel
{
  "schemaVersion": 1,
  "projectId": "marca-salao",
  "catalogVersion": "1",
  "profileId": "instagram-reels-video",
  "profileRevision": 2,
  "mediaKind": "video",
  "video": {
    "width": 1080,
    "height": 1920,
    "aspectRatio": "9:16",
    "fps": 30
  }
}
```

`pendencias de fonte: (nenhuma)` **não** é "tudo certificado": as pendências deste perfil viraram regra (`R-IG-09`), e a linha acima do stderr continua dizendo que o plano não informou contexto. O que ainda exige inspeção de arquivo está na linha seguinte, inalterada.

Saída medida de (B), exit **1**, stdout com **0 bytes** (stderr integral, sem supressão):

```
Avisos (camada plano):
  OUTPUT_PLAN_CONTEXT_NOT_DECLARED @ruleContext: Rule "R-IG-09" (@api-publishing) cannot be assessed because the document declares no context; structural validity does not confirm an official requirement.
Avisos (camada composicao):
  COMPOSITION_RENDERER_UNDECIDED @renderer.adapter: renderer.adapter is "undecided": no renderer is adopted by this composition yet.
Erros (camada compatibilidade):
  OUTPUT_COMPAT_PROFILE_MISMATCH @format.profile: composition.format.profile "vertical-social" is not the plan profile "instagram-reels-video".
Avisos (camada compatibilidade):
  OUTPUT_PLAN_CONTEXT_NOT_DECLARED @ruleContext: Rule "R-IG-09" (@api-publishing) cannot be assessed because the document declares no context; structural validity does not confirm an official requirement.

pendencias de fonte: (nenhuma)
requer inspecao: media-file, codec, bytes, audio-streams, publication
compatibilidade: composicao "pilot-composition" incompativel (1 erro(s))
```

**(B) não é caso feliz — e é o caso mais importante da seção.** `marca-salao-pilot.composition.json` continua **válida** no validador genérico de Composition v1 (perfil opaco `vertical-social`, 1080×1920 @30) e falha só na compatibilidade, com `OUTPUT_COMPAT_PROFILE_MISMATCH`, porque `format.profile` ≠ `profileId` do plano. Ela é mantida exatamente para mostrar essa diferença, e **não foi substituída nem editada**. Para que a divergência exista, o manifesto técnico precisa aceitar a composição antiga primeiro: `validateComposition` exige `composition.projectId === project.id`, então o manifesto de demonstração **reusa o `id` `marca-salao`** e lista `vertical-social` no allowlist. Há um teste que prova a aceitação da composição antiga **antes** do teste de divergência (`platform/tests/output-plan-examples.test.ts`), porque a ordem das duas asserções é o que separa "o núcleo rejeitou" de "o plano divergiu".

### 8.0.1 (C) medida na R001-05: regra aplicada que o plano não consegue aferir

Exit **0**; o stderr abre com os três avisos documentais e a saída humana traz o contexto declarado:

```
Avisos (camada plano):
  OUTPUT_PLAN_RULE_NOT_ASSESSABLE @video: Rule "R-FB-06" (@api-publishing) is stated for the declared context but needs data this document does not carry; nothing was verified.
  OUTPUT_PLAN_RULE_NOT_ASSESSABLE @video: Rule "R-FB-08" (@api-publishing) is stated for the declared context but needs data this document does not carry; nothing was verified.
  OUTPUT_PLAN_RULE_NOT_ASSESSABLE @video: Rule "R-FB-09" (@api-publishing) is stated for the declared context but needs data this document does not carry; nothing was verified.
Plano de saida canonico — facebook-reels-video — Reels do Facebook (revisao 2)
  projeto: marca-salao | catalogo: v1
  destino: facebook/reels | midia: video | resolucao: 1080x1920 (9:16) | fps: 30
  contexto declarado: api-publishing
  capacidade de catalogo: tool-export-observed
pendencias de fonte: P-FB-03
requer inspecao: media-file, codec, bytes, audio-streams, publication
```

Leia os três avisos como o desenho manda: `R-FB-06` pede duração (o plano não tem; a soma de cenas mora na Composition), `R-FB-08` é a proporção declarada sem `value` (duas relações certificadas em páginas de objetos diferentes), `R-FB-09` é contêiner (só o arquivo diria). **`R-FB-07` não aparece** — é `min-dimensions 540×960`, avalia-se da geometria do plano e o preset 1080×1920 a cumpre. Um perfil que antes não tinha nenhuma regra agora tem quatro aplicadas, três delas sem poder de erro, e o relatório continua dizendo exatamente o que não foi verificado.

### 8.1 Contrato entregue de `content:profiles`

Flags `--network` `--publication` `--media` `--project` `--json`. Exit **0** listagem produzida (lista **vazia** é resultado válido: `--network youtube --publication stories` não tem perfil) · **1** JSON legível com manifesto rejeitado · **2** enum inválido, flag duplicada, flag desconhecida, valor ausente, arquivo inexistente ou JSON malformado.

O documento `--json` tem exatamente `catalogVersion, filters, project, counts, profiles, diagnostics, summary`; cada entrada de `profiles` tem `id, name, revision, network, publication, mediaKind, width, height, aspectRatio, fps, exportState, exportEvidence, pendingRuleIds, availability, blockCode, blockReason`. O formato completo e os estados estão contratados em `platform/README.md` (*Contrato de `content:profiles`*).

- **Estados de disponibilidade:** `allowed` (o `id` está em `outputProfiles`), `blocked` (ausente do allowlist → `OUTPUT_PROFILE_NOT_ALLOWED`, ou manifesto rejeitado → `OUTPUT_PROJECT_INVALID`) e `not-consulted` (**sem `--project` — nunca "permitida"**). `fps` é `null` em perfil de imagem.
- **Manifesto inválido não apaga o catálogo:** a lista filtrada sai primeiro, com `counts.blocked` contado pelo manifesto, `diagnostics` com os issues do validador e o diagnóstico em stderr (`Manifesto rejeitado: OUTPUT_PROJECT_INVALID — …`), e o processo termina **1**.
- **Nenhum dicionário paralelo:** a lista vem de `listOutputProfiles`, o allowlist de `projectAllowedProfiles` (a mesma função do resolvedor) e os códigos de bloqueio são os códigos estáveis do contrato do plano.

### 8.2 Contrato entregue de `content:plan-output`

Flags `--project` + `--profile` **obrigatórias**, mais `--network` `--publication` `--media` `--rule-context` `--composition` `--json`. Exit **0** plano resolvido e, se informada, composição compatível · **1** plano, seleção ou compatibilidade inválidos · **2** uso, arquivo ausente ou JSON malformado.

- Em `--json` o stdout é **exatamente** `resolution.plan` (dois espaços, newline final). O byte a byte é re-lido pelo schema e por `validateOutputPlan` sem edição, e é o mesmo byte que gerou os fixtures de §9.
- A verificação de Composition acontece **antes** de emitir, para nunca imprimir um plano recém-resolvido cuja composição já se sabe que não casa.
- Avisos e códigos por camada vão para **stderr nos dois modos, inclusive no sucesso**: "não há o que certificar" não é erro. `pendencias de fonte:` e `requer inspecao:` **dependem do modo** — em `--json` vão para stderr (o stdout é só o artefato), e no modo humano fazem parte do bloco humano impresso no **stdout**, como o caso (C) mede acima. Os dois estados estão assertados em teste (`platform/tests/output-clis-process.test.ts`), então a diferença é contrato, não acidente. Na falha o stdout fica **vazio nos dois modos** (humano e JSON).
- **`--composition` em plano de imagem é recusado** com `OUTPUT_COMPAT_IMAGE_NO_COMPOSITION` — `fps` nunca é fabricado.
- Filtros redundantes junto do ID são aceitos se concordarem e rejeitados se contradizerem (`OUTPUT_PROFILE_AMBIGUOUS_SELECTION`).
- A saída humana traz ID, nome, destino (rede/publicação), tipo de mídia, resolução, fps quando existir, contexto declarado, capacidade observada no catálogo e o bloqueio quando houver.

## 9. Exemplos e fixtures entregues (R001-04, re-geridos na R001-05)

- `platform/examples/projects/marca-salao-social.project.json` — manifesto **técnico** com allowlist social explícita: `vertical-social` (para a divergência), `instagram-feed-image-square`, `instagram-reels-video`, `facebook-reels-video`, `youtube-video-horizontal`, `youtube-shorts`. Os exemplos oficiais atuais (`marca-salao.project.json`, `fixture-project.project.json`) continuam **intactos**.
- `platform/examples/compositions/marca-salao-social-reel.composition.json` — composição positiva em `instagram-reels-video` (3 cenas, 14 000 ms, `renderer.adapter: "undecided"`, sem áudio), com `metadata.description` declarando que não é peça aprovada nem campanha publicada.
- `platform/examples/output-plans/*.output-plan.json` — **5 planos**: imagem quadrada, Reels do Instagram, Reels do Facebook, vídeo horizontal do YouTube e Shorts com `ruleContext: "studio-upload"` explícito. Cada arquivo foi **gerado pelo stdout da CLI** (não digitado) e o teste compara os bytes do stdout com os bytes do fixture, então o exemplo que se lê no repositório é o que a ferramenta produz. Cada plano também passa por round-trip ajv + `validateOutputPlan` com o projeto correspondente.
- **Re-gerados na R001-05:** o diff dos cinco fixtures é de exatamente **cinco linhas**, uma por arquivo, todas `profileRevision` — `1 → 2` nos **quatro fixtures** cujo perfil subiu de revisão e `2 → 3` no `youtube-shorts-studio-upload`, que já estava em 2. São cinco arquivos, não cinco perfis: a matriz de §3 tem **doze** perfis e todos tiveram a revisão alterada nesta etapa — onze de `1 → 2` e o `youtube-shorts` de `2 → 3` — mas só os cinco que têm plano versionado aparecem aqui. Geometria, `fps`, `mediaKind`, `catalogVersion` e `projectId` não mudaram: promover regra muda o que o **relatório** diz, e o plano canônico só carrega parâmetros resolvidos. É essa a razão de o exemplo ser gerado e não editado — se a revisão tivesse sido digitada à mão, o fixture provaria a intenção de quem escreveu, não o comportamento da ferramenta.
- `platform/README.md` documenta os dois contratos, os comandos executados, a forma JSON da listagem, os estados de disponibilidade e a diferença entre **formato conhecido pelo catálogo** e **opção habilitada por aquele projeto**.

### 9.1 Formato → template/gerador observado, com o limite real de exportação

“Observado” é o que a ferramenta desta caixa **exporta hoje**; não é limite oficial da rede, e nada aqui liga `platform/` a um gerador.

| Perfil do catálogo | Onde já é exportado | Limite real observado na exportação |
| --- | --- | --- |
| `instagram-feed-image-square`, `facebook-feed-image-square` (1080×1080) | `FORMATS['quadrado']` (`marcas/marcasalao/comfyui/custom_nodes/servidor02_gemini/brand.py:14`), `sizes` (`marcas/marcasalao/comfyui/marcasalao_export.py:47`), ratio `1:1` (`.../artwork.py:11`) | PNG 1080×1080. A rota de API do Instagram exige JPEG (§10.1) — o descompasso continua **verificação pendente**, não diagnóstico de falha |
| `*-feed-image-portrait` (1080×1350) | `FORMATS['vertical']` + `RATIOS['vertical'] = 4:5` | PNG 1080×1350; nenhum preset de ferramenta de vídeo nessa geometria |
| `*-stories-image` (1080×1920) | `FORMATS['stories']` + `RATIOS['stories'] = 9:16` | PNG 1080×1920 |
| `instagram-stories-video`, `facebook-stories-video` | `templates/story_reel_vertical/index.html:165-167` (1080×1920, `data-duration="8"`), `tools/build_video.py:30` | Preset de **8 s** a 1080×1920 @30 com `libx264`; `duration`, `resolution` e `fps` são parâmetros do script, não limites do núcleo. Desde a R001-05 as duas redes têm **o mesmo teto** para este destino (`R-IG-08` e `R-FB-03`: 60 s), e o Facebook acrescenta mínimo de 540×960 (`R-FB-04`) e faixa de 24–60 fps (`R-FB-05`) |
| `instagram-reels-video`, `facebook-reels-video` | mesmo template vertical + `tools/edit_link_reel.py:55-57` + `templates/reel_link_overlay/hyperframes.json:4-8` (1080×1920, `fps: 30`, `duration: 27`) e `templates/reel_link_overlay/index.html:140-142` (`data-duration="27"`) | **`edit_link_reel.py` não parametriza geometria:** escala e crop fixos em 1080×1920 com `fps=30` — é o único resultado possível por aquele caminho. `reel_link_overlay` traz **27 s** no preset; é duração de template, não autorização de duração. **O par mais perigoso da tabela:** mesma geometria, tetos oficiais dez vezes diferentes — `R-IG-09` permite 900 s no Instagram e `R-FB-06` permite 90 s na Página do Facebook. Um reel de 5 minutos exportado uma vez e publicado nos dois lugares é válido num e estoura no outro, e o verificador só o vê quando o contexto é declarado e a soma de cenas existe |
| `youtube-video-horizontal` (1920×1080 @30) | `templates/youtube_horizontal/index.html:199-201` (1920×1080, `data-duration="10"`); `tools/build_video.py` aceita `resolution="1920x1080"` | 10 s no template. **Nenhum gerador dedicado de YouTube existe** (§1.3): o perfil é dado de catálogo com canvas mapeado, não pipeline |
| `youtube-shorts` (1080×1920 @30) | reuso do caminho vertical acima | Nenhum limite de exportação local: a borda certificada (180 s, `R-YT-01`) é a **duração declarada na Composition**, somada das cenas — nunca o arquivo gerado |

Consequência registrada: `data-duration`/`duration` são **presets de template**, não limites oficiais, e nenhum `renderer.adapter` passa a ser “pronto” porque o canvas coincide (§1.3). O catálogo conserva `preset-only` → `canvas-template-mapped` → `tool-export-observed` exatamente para que essa diferença não se perca.

## 10. Lacunas e riscos descobertos nesta leitura

1. **PNG × JPEG continua verificação pendente — e agora com número oficial dos dois lados.** A produção atual do Marca Salão exporta PNG (`WORKFLOW.md:40`, `marcasalao_export.py:47`), e a publicação de imagem do Instagram por API aceita **somente JPEG** (`S-IG-API`, `R-IG-01`), inclusive em Stories (`R-IG-07`, certificado na R001-05). O outro lado é o **Facebook**: a fonte própria (`R-FB-01`) aceita PNG. Ou seja, uma arte quadrada em PNG pode ser rejeitada por um destino e aceita pelo outro — e o núcleo não abre arquivo nenhum para descobrir. Nada aqui comprova falha no fluxo de Postiz, e nada autoriza conversão ou alteração de produção nesta R001; o item fica como **verificação pendente entre formato produzido e rota pretendida** (§6.2.1, `image-format`).
2. **Compartilhamento de Stories ≠ API — resolvido, com a separação preservada.** `R-IG-04`/`R-IG-05` vêm da página de *sharing-to-stories* (app) e seguem `informational`: mínimo 720×1280 e 9:16/9:18 **não** validam plano de API. O que a R001-05 certificou é a rota de API por regra própria (`R-IG-07`: JPEG, 8 MB, 9:16 recomendado), então a pergunta que era pendência virou duas respostas com fontes diferentes — e não uma fusão das duas.
3. **Facebook tinha fonte; o que não tinha era caminho.** Os cinco perfis do Facebook saíram da R001-05 com **nove** regras oficiais aplicadas (`R-FB-01…09`) e duas pendências nomeadas (`P-FB-01` dimensão de foto, `P-FB-03` bytes de vídeo). A R001-02 havia registrado "não consultado com sucesso" a partir de uma única página (`docs/video-api/`), que de fato só aponta para "Reference" — as páginas específicas abriram. Lição: **ausência de evidência onde se procurou não é ausência de evidência**; e mesmo assim a regra do Instagram **não** migrou, porque a fonte própria do Facebook a contradisse.
4. **O novo schema precisa ser executado.** Em R001-03 o `output-plan.schema.json` **deve** ser compilado e executado por ajv no harness de contratos (`platform/tests/contract-harness.ts`, precedente: `projectSchemaCheck`/`compositionSchemaCheck` em `:69-70`), com o corpus estrutural comparado ao validador do core. **Não existe mais a alternativa de deixá-lo sem execução.** O que continua legítimo é separar as coisas: relações entre projeto e catálogo são regras semânticas que o JSON Schema não expressa e vivem só nos validadores.
5. **Colisão de guards entre branches.** `platform/tests/beat-plan-validation.test.ts` (só em `codex/core-beat-plan-v1`, **não** nesta base) asserta o mundo fechado de `readdirSync(src)` e `schemas/`. Quando BeatPlan e R001 coexistirem, esse guard precisa **ganhar** as novas entradas — não ser enfraquecido. Documentado agora porque a decisão de arquitetura (subpasta `src/output-profiles/`) afeta esse teste.
6. **Guardas a atualizar nesta base:** `platform/tests/build-portability.test.ts:58` (`readdirSync(distDir, { recursive: true })`), `:100-102` (scripts declarados, `dependencies === undefined`, devDependencies exatamente `@types/node`, `ajv`, `typescript`).
7. **Filtro de paths do CI.** `.github/workflows/platform-validation.yml` só dispara em `platform/**` ou no próprio workflow. **Um commit somente de documentação não roda o gate** — em R001-05, ausência de check não pode ser lida como sucesso.
8. **Sem nova dependência.** Nada aqui exige pacote novo: TypeScript compila dados declarativos, ajv já é dev, e a suíte usa `node:test`. Se surgir necessidade concreta, a regra do projeto é parar, explicar e não instalar em silêncio.
9. **A subpasta exigiu tornar os guards recursivos (feito na R001-02).** `project-validation.test.ts` e `composition-validation.test.ts` varriam `readdirSync(src)` **raso** e chamavam `readFileSync` em cada entrada; com `src/output-profiles/` isso virava `EISDIR`. Os dois passaram a caminhar recursivamente — o guard fica **mais forte** (subpastas entram na varredura), não mais fraco. Consequência prática: a lista `forbidden` pré-existente desses guards contém nomes de ferramenta (`hyperframes`, `ffmpeg`, `capcut`), então **evidência interna no núcleo não pode citar `templates/*/hyperframes.json`**; `D-LOCAL-05` (fps 30) aponta para §1.2, que registra o caminho completo. Isso não é a proibição genérica de domínio que a revisão rejeitou — é o guard que já existia nesta base e que a R001 respeita.
10. **A fonte oficial se contradiz dentro da mesma página — e o catálogo não decide por conta própria.** `S-FB-STORIES` imprime "Duration: 3 to 90 seconds." na tabela de especificações e "A video story can not exceed 60 seconds" em Limitations. `R-FB-03` promove o teto estrito (nenhuma das duas autoriza 90 s em Story de vídeo), mas isso é **julgamento documentado**, não fato da página; a `note` preserva os dois números para o revisor poder discordar. Analogamente, `R-FB-08` ficou **sem `value`** porque a família de páginas declara duas relações diferentes para objetos distintos. Risco real de uma releitura apressada: "resolver" a contradição escolhendo o número mais conveniente.
11. **Tradução automática já mudou um número nesta plataforma.** A variante pt-BR de `S-FB-STORIES` traduz "3 to 90 seconds" por **"3 a 9 segundos"**. Uma citação colada da locale errada teria entrado no catálogo como limite nove vezes mais estrito que o certificado, com URL oficial e tudo. Mitigação adotada e verificável: toda citação da R001-05 saiu de locale `en`, e o teste que fixa a regra (`platform/tests/output-profiles-catalog.test.ts`) asserta a presença das **duas** strings na `note` de `R-FB-03` — a inglesa e a traduzida errada — para a releitura não "limpar" o defeito.
12. **Cadência e cota ficaram de fora por decisão, não por esquecimento.** 100 posts/24 h, 400 contêineres/24 h, 30 Reels/24 h e 100 uploads/dia são fatos certificados (§2.2.3) e nenhum é forma de mídia. Se a R002 publicar, vai precisar de modelo de **conta e agenda** — que não existe aqui, e inventar campo de cota no OutputPlan seria certificado fictício. Por enquanto só `PN-YT-02` entrou, como nota, porque a cota era o núcleo da pergunta de `P-YT-02`.
13. **Duas redes, mesma geometria, tetos dez vezes diferentes.** `R-IG-09` (900 s) e `R-FB-06` (90 s) valem para o mesmo preset 1080×1920 @30. O verificador compara **um perfil por vez** (D-06: plano único por seleção), então a divergência aparece em duas resoluções distintas, não numa só. Se a produção publicar o mesmo arquivo nos dois destinos, quem precisa saber disso é o operador — o catálogo informa, não autoriza variação automática.
14. **O número certificado de hoje é o de uma versão de API.** As citações da Meta saem da referência Graph **v27.0** (`S-IG-USERMEDIA`, `S-FB-PHOTOS`); a página de Stories declara atualização em 30/07/2026. Nada no catálogo expressa "válida para v27.0", e a URL não carrega a versão. Se a Meta publicar v28 com especificações diferentes, o `source.accessedOn` é o que permite ao revisor datar a evidência — e é a razão de a revalidação continuar sendo obrigação de etapa, não detalhe de implementação.

## 11. Critérios de teste por etapa

**R001-02 (catálogo):** `profileId` únicos e os 12 IDs da matriz presentes; `findOutputProfile` resolve cada um e devolve `null` para inexistente; geometria × `aspectRatio` coerente (1080×1350→4:5, 1080×1920→9:16, 1920×1080→16:9, 1080×1080→1:1); perfil de imagem não tem `fps` nem `plannedContainer`; perfil de vídeo tem `fps ≥ 1`; **união discriminada** de `CatalogRule` respeitada — `official-rule` tem `source` presente, `internal-default` tem `evidence` presente, `pending-source` não tem `value` nem `source` (ausência, não `null`); todo `ruleId`/`pendingId`/`noteId` referenciado resolve no registro, com `network` e `contexto` compatíveis; regra de outra rede nunca aparece num perfil; `D-LOCAL-*` com `network: null` é compartilhável; estado `applies` só existe quando rede+publicação+contexto batem com a fonte; `informational` e `not-evaluated` jamais viram erro; filtros por rede/publicação/mídia; cobertura mínima ≥ 1 imagem, 1 Reels por rede, 1 Shorts; **orientação permitida pelo destino distinta da geometria exata do preset** (Shorts: condição quadrada-ou-vertical ≠ lista 1:1/9:16); combinações proibidas checadas em tempo de tipos com `@ts-expect-error`, inclusive através de variável intermediária.

Sobre independência (correção da revisão): o que é proibido no núcleo é **dado específico de cliente** — nome de marca, ID de canal, domínio comercial, tema editorial, caminho de projeto. **URL oficial de fonte e evidência interna do repositório são dados permitidos e necessários** (`RuleSource.url`, `evidence`). Não existe, e não deve ser criado, teste que proíba qualquer domínio ou nome de ferramenta em `platform/src`.

**R001-03 (resolver + plano + compatibilidade):** ID desconhecido; perfil fora da allowlist; campos cruzados imagem↔vídeo; dimensão divergente do preset; revisão inválida; projeto divergente; `catalogVersion` desconhecida; bordas de limites verificados — Shorts com `totalDurationMs` **180000 (aceita) e 180001 (rejeita)**, e isso exige declarar um contexto **do escopo** de `R-YT-01` — na R001-03 era apenas `studio-upload`; desde a correção de escopo da R001-04, `in-app` também vale e a borda é testada nos dois (§2.1.1, §6.4, D-19): sem contexto declarado a mesma Composition continua estruturalmente válida e gera **aviso**, nunca erro. Os dois cenários são testados, para registrar o alcance da validação; `R-IG-04` (720×1280) exercitado como informação de contexto app, nunca como validação de API; `resolveOutputPlan` devolve `{ plan, report }` com `plan` presente só no sucesso; **round-trip** do plano (serializar → reler → `validateOutputPlan(plano, projeto)` → relatório **igual** ao da resolução, com `ruleContext` preservado; `validateOutputPlan` devolve relatório, não plano — §7); a CLI consumindo o plano canônico, sem reconstruí-lo de campos ecoados, passa a ser testada em R001-04, onde a CLI existe; corpus ajv × validador do core comparados para o novo schema; entrada não mutada; dois runs produzem SHA-256 igual do JSON; corpus antigo continua com comportamento idêntico.

**R001-04 (CLI como processo):** listagem com e sem filtro para as três redes; `--project` indica permitido/bloqueado com motivo; JSON do stdout parseável; stderr contém o operacional; exit 0/1/2 em seleção válida/incompatível/uso-arquivo-JSON; `--composition` em plano de imagem recusado; argumento desconhecido tratado como uso; byte a byte determinístico; nenhuma mídia gerada, nenhum rascunho de campanha, nenhuma chamada paga.

Medido nesta etapa (`platform/tests/output-clis-process.test.ts`, 24 testes; `platform/tests/output-plan-examples.test.ts`, 9 testes): listagem sem projeto com `notConsulted` = 12 e chaves do JSON em ordem canônica; filtros por rede/publicação/mídia inclusive a combinação **válida porém vazia** (`youtube` + `stories` → 0 perfis, exit 0); allowlist com habilitado e bloqueado (`OUTPUT_PROFILE_NOT_ALLOWED`); manifesto rejeitado mantendo a lista com `counts.blocked` e `diagnostics = ['PROJECT_SCHEMA_VERSION_UNSUPPORTED']`, exit 1; sete casos de erro de uso (enum inválido, `--rule-context` na CLI que não o aceita, flag duplicada, `--json --json`, flag desconhecida, flag sem valor, flag final sem valor) todos exit 2 com stdout vazio; arquivo ausente e JSON malformado exit 2; paridade byte a byte do stdout com `resolveOutputPlan` em memória; pendências e `requer inspecao` presentes no stderr **do sucesso**; `OUTPUT_PLAN_RULE_NOT_APPLIED` com contexto fora do escopo (`api-publishing`) mostrando o escopo real `@in-app, @studio-upload`; as três camadas de diagnóstico rotuladas num mesmo caso; não mutação da entrada; e as duas CLIs antigas ainda exit 0 sobre os pares oficiais.

**R001-05 (revisão):** jornada completa demonstrada (listar → allowlist → selecionar → plano → validar composição); independência de marcas; falhas úteis; nem recomendações nem defaults internos viraram limites oficiais; nenhum relatório alega ter validado bytes, codec, arquivo ou publicação; compatibilidade de todas as CLIs e fixtures antigas; contagens de teste **medidas de novo**, não herdadas da PR #6.

**R001-05 (resolução das pendências de fonte) — o que os testes fixam:** cada regra promovida tem ID, classe, escopo de contextos e `value` **exatos** assertados contra o registro (`platform/tests/output-profiles-catalog.test.ts`), inclusive os sete casos documentais em que `value` deve ser **ausente** (`R-IG-06`, `R-IG-10`, `R-FB-05`, `R-FB-08`, `R-YT-05`, `R-YT-06`, `R-YT-07`) — a ausência é a asserção, não uma lacuna. As quatro pendências restantes são verificadas por ID, rede, contexto e pelo enunciado dizer **o que falta** (`/n[ãa]o |sem /`), e a lista antiga de pendências extintas é conferida como extinta. Cada `source` carrega URL + título + `accessedOn` com horário UTC da consulta + citação literal; o teste asserta que a contradição interna da Stories API (inglesa e a traduzida "3 a 9 segundos") continua **registrada** na `note` de `R-FB-03`. Comportamento avaliado, medido pela CLI como processo: `R-IG-09` na borda 900000 ms (exit 0) / 900001 ms (exit 1, stdout vazio, `OUTPUT_COMPAT_DURATION_EXCEEDED`, origem `"R-IG-09" @api-publishing"`); `R-FB-07` cumprido pelo preset e por isso **sem** aviso; `R-FB-06`/`R-FB-08`/`R-FB-09` como `OUTPUT_PLAN_RULE_NOT_ASSESSABLE`; `applies` de contexto não declarado virando `OUTPUT_PLAN_RULE_NOT_APPLIED` com o escopo real impresso; e nenhum perfil do Facebook referenciando regra `R-IG-*` (e vice-versa).

Medido nesta etapa, depois das resoluções: **510 testes / 510 pass / 0 fail / 0 skipped** (eram 495 na R001-04: **+15**, líquido por arquivo **+12** `output-profiles-catalog.test.ts`, **+2** `output-clis-process.test.ts`, **+1** `output-plan-validation.test.ts`), com **288 contratos / 288 pass / 0 fail** — a superfície de contratos não mudou, porque promover regra é conteúdo do registro, não forma do schema. Gates em Node **v22.23.2** / npm **10.9.8**: `npm ci` (**8 pacotes, 0 vulnerabilidades**, `package.json` e lockfile intactos), `run clean`, `run typecheck`, `run build`, `npm test` e `npm run test:contracts` todos exit **0**; as **quatro** CLIs executam (as duas legadas exit **0** com `--project`/`--composition`, `content:profiles` exit **0**, `content:plan-output` exit **0** no sucesso e **1** na divergência de perfil com stdout de **0 bytes**); `npm ls --omit=dev --all` continua imprimindo a árvore vazia e `git diff --check`, limpo.

## 12. Gate e verificação

Sequência obrigatória em `platform/` com Node 22: `npm ci`, `npm run clean`, `npm run typecheck`, `npm test`, `npm run test:contracts`; mais `npm ls --omit=dev --all` (vazio de runtime), `git diff --check`, e ausência de `dist/`/artefatos rastreados. Matriz Linux/Windows × Node 22/24 e `scripts/gate-step.sh` permanecem como estão; os testes novos rodam **no gate existente** (`npm test` já pega `dist/tests/**/*.test.js`), sem refatorar workflows.

## 13. Checkpoints da sequência

| Etapa | Concluída quando | Commit |
| --- | --- | --- |
| **R001-01** | este documento existe com base/HEAD, capacidade observada, matriz, regras verificadas × pendentes, arquivos previstos, interfaces, critérios de teste e os cinco checkpoints; commit local de documentação | **concluída** — base `0c97c2a` (main, PR #6 integrada); commits locais `55bfc0c` (desenho) e `32138bd` (citacao da independencia) |
| **R001-02** | catálogo compilando, testes de invariante verdes, checkpoint atualizado com perfis criados e pendências reais | **concluída** — 12 perfis (6 imagem / 6 vídeo), 21 entradas no registro (4 `requirement`, 2 `recommendation`, 5 `internal-default`, 10 `pending-source`) + 1 `PolicyNote`; 16 testes novos; gates em Node 22: **324 testes / 0 falhas / 0 skipped** e **219 contratos / 0 falhas**; commits `fe9d8d7` (desenho corrigido) e `195e7e3` (catálogo, testes e guards recursivos) |
| **R001-03** | `resolveOutputPlan` + `validateOutputPlan` + compatibilidade de Composition verdes, schema `output-plan` fechado, corpus antigo inalterado | **concluída** — 4 módulos novos em `platform/src/` (`output-plan-contract.ts`, `validate-output-plan.ts`, `resolve-output-profile.ts`, `validate-composition-output.ts`) + `platform/schemas/output-plan.schema.json`; `ruleContext` no plano, no schema e no relatório (§2.1.1). Gates em Node 22 (**v22.23.2**, npm **10.9.8**): `npm ci` (8 pacotes, **0 vulnerabilidades**), `run clean`, `run build`, `run typecheck`, `npm test` e `npm run test:contracts` todos com exit 0 — **454 testes / 0 falhas / 0 skipped**, sendo **288 contratos / 0 falhas**; ou seja, **130 testes novos** (69 de paridade ajv × core em `contracts/output-plan-schema.test.ts`, 61 nas três suítes de unidade). Corpus do OutputPlan separado em **estrutural** (os dois motores chegam ao mesmo veredicto; 49 casos) e **semântico** (autoridade do core, veredicto do schema registrado por caso; 17 casos). Os doze perfis resolvem, os exemplos oficiais e o perfil genérico legado continuam válidos. |
| **R001-04** | `content:profiles` e `content:plan-output` funcionais como processo, exemplos de projeto/planos entregues, correspondências com templates documentadas com limitações reais | **concluída** — escopo de regra oficial virou **lista de contextos** (`contexts`, decidido por `contexts.includes(contextoDeclarado)` no avaliador já existente, sem tabela paralela de limites e sem `if` por rede ou `profileId`; `youtube-shorts` sobe de revisão 1 → 2 com a citação literal revalidada), as duas CLIs existem (`src/output-profiles-cli.ts`, `src/output-plan-cli.ts`, camada compartilhada `src/cli-input.ts`) com **24 testes de processo** e os exemplos executam: manifesto técnico social, composição positiva (3 cenas, 14 000 ms) e **5 planos gerados pelo stdout**, comparados byte a byte e relidos por ajv + `validateOutputPlan` (**9 testes**). A borda de 180 s de Shorts roda nos **dois** contextos pelo `--composition`: `180000` → exit 0 e `180001` → exit 1 com `OUTPUT_COMPAT_DURATION_EXCEEDED` e `"R-YT-01" @in-app, @studio-upload`. Gates em Node 22 (**v22.23.2**, npm **10.9.8**) após `npm ci` (**0 vulnerabilidades**, lockfile intacto): `run clean`, `run typecheck`, `run build`, `npm test` e `npm run test:contracts` todos com exit 0 — **495 testes / 0 falhas / 0 skipped**, ou seja **+41** sobre os 454 da R001-03 (líquido por commit: **+7** da correção de escopo, 9 `test(` novos e 2 consolidados; **+25** das CLIs; **+9** dos exemplos) e **288 contratos / 0 falhas**. Higiene medida: `npm ls --omit=dev --all` imprime a árvore vazia, `dependencies` continua inexistente, `git diff --check` limpo e `dist/` segue ignorado (nada de artefato rastreado). Commits locais `9521de6` (escopo), `73d5a6b` (CLIs), `29e3955` (exemplos), `8562cc3` (README + checkpoint) e o commit de documentação que traz esta linha. |
| **R001-05** | jornada demonstrada, gates rodados com contagens medidas, README e este documento atualizados, descrição de PR pronta | **concluída** — as **dez** pendências da R001-02 viraram **quatro**: **8 extintas** por página de primeira mão, `P-FB-01` **estreitada** (formatos e peso certificados, **dimensão** não), `P-HELP-01` mantida (a central do app é landing sem número) e **2 novas** abertas pela própria leitura (`P-FB-03` bytes de vídeo, `P-YT-03` contêiner/peso de Short). Promovidas **17 `OfficialRule`** (`R-IG-06…10`, `R-FB-01…09`, `R-YT-05…07`) + **1 `PolicyNote`** (`PN-YT-02`), cada uma com URL, título, `accessedOn` com hora UTC e citação literal da locale `en`: a variante pt-BR da Stories API imprime **"3 a 9 segundos"** para "3 to 90 seconds", e a `note` de `R-FB-03` guarda as duas strings. Registro medido no build: **32 entradas** (19 `requirement`, 4 `recommendation`, 5 `internal-default`, 4 `pending-source`) + **2 `PolicyNote`**; das **23** oficiais, **16** têm `value` e **7** são documentais — `RuleValue` **não** foi aumentada (§2.2.3). Nos perfis, **11** sobem 1 → 2 e `youtube-shorts` 2 → 3; os **cinco** exemplos re-geridos mudam **exatamente cinco linhas**, todas `profileRevision`. Gates em Node 22 (**v22.23.2**, npm **10.9.8**) após `npm ci` (**8 pacotes, 0 vulnerabilidades**, `package.json` e lockfile intactos): `run clean`, `run typecheck`, `run build`, `npm test` e `npm run test:contracts` com exit **0** — **510 testes / 510 pass / 0 fail / 0 cancelled / 0 skipped** (**+15** sobre os 495 da R001-04, líquido por arquivo: **+12** `output-profiles-catalog.test.ts`, **+2** `output-clis-process.test.ts`, **+1** `output-plan-validation.test.ts`) e **288 contratos / 0 falhas** (mesmo total da etapa anterior). As quatro CLIs executam: `content:validate-project -- --project …` e `content:validate-composition -- --project … --composition …` com exit **0**, `content:profiles` exit **0**, `content:plan-output` exit **0** no caminho feliz e exit **1** com stdout de **0 bytes** na divergência de perfil (§8). Higiene medida: `npm ls --omit=dev --all` imprime a árvore vazia, `git diff --check` limpo, nenhum artefato rastreado e nenhuma credencial no diff. Commits locais `9a977c7` (regras, catálogo e testes) e `e1caf5e` (exemplos), mais o commit de documentação que traz esta linha. Descrição de PR **redigida e entregue na conversa** — nenhum PR aberto, por restrição explícita do titular. |

**Revisão independente do checkpoint fechado.** Depois de `e1caf5e` e do primeiro commit de documentação da etapa, este documento foi lido por inteiro contra `rules.ts`, `catalog.ts`, os exemplos, os testes e o histórico, por um revisor sem o contexto da conversa. Onze achados: **três já estavam resolvidos** na hora da correção (a distinção entre `P-FB-01` estreitada e `P-HELP-01` revalidada sem número, as linhas "não existe no registro" de `R-IG-02`/`R-IG-03` e o particípio solto em §11) e **oito procediam**, corrigidos nos commits `75d80b4`, `5e9a4e0` e no commit de documentação que traz este parágrafo. Eram defeitos de **prosa e de referência**, não de medida: uma data que nenhuma fonte desta etapa sustenta (o custo antigo de 1600 unidades, que a `S-YT-QUOTA` registra como mudança de 2025-12-04 e o texto chamava de "número de 2024"), dois ponteiros `platform/README.md:11` desatualizados pela linha que a terceira fatia ganhou, uma referência `AGENTS.md:48` que cai na seção do Multitrack Hub em vez da arte quadrada compartilhada (`:52-54`), quatro defeitos de linguagem/acentuação e uma verificação por `grep -c` citada sem o arquivo, as contagens nem a limitação de que o anexo não está no clone. **Nenhum número deste documento mudou com essa revisão** — as contagens de registro, revisões, fixtures, testes e portões continuam as medidas acima, e os portões foram rerodados depois das edições de texto com o mesmo resultado.

Cada etapa seguinte começa depois de concluir e conferir a anterior, na mesma branch. Os prompts antigos 08–10 (BeatPlan, consumidor Multitrack Hub, piloto de mídia/texto) **não** se misturam aqui; quando forem executados, devem **reutilizar** o catálogo desta R001 em vez de criar outra tabela de formatos.

## 14. Decisões pequenas registradas

| ID | Decisão | Motivo |
| --- | --- | --- |
| D-01 | Subpasta `platform/src/output-profiles/` | sugerida no pacote; `tsconfig.json` já inclui `src/**/*.ts`, então o build e `dist/tests/**/*.test.js` continuam válidos |
| D-02 | IDs de perfil kebab-case, reutilizando `outputProfiles` como allowlist | sem campo novo na v1; a seleção passa a ser explícita sem migração |
| D-03 | Rótulo humano em **português** como *dado* do catálogo; códigos e mensagens de relatório continuam em inglês | atende o pedido de nome legível sem quebrar a convenção executável existente (`VALID_SUMMARY`, `issue()`) |
| D-04 | O núcleo proíbe **dado específico de cliente** (nome de marca, ID de canal, domínio comercial, tema editorial, caminho de projeto); **URL oficial de fonte** e **evidência interna do repositório** são dados permitidos e necessários | `RuleSource.url` e `evidence` existem para registrar proveniência; proibir domínio tornaria o catálogo incertificável. A independência continua em `platform/README.md:12` e `:17-19` |
| D-05 | Registro de regras separado, referenciado por ID; geometria compartilhada por constante | uma fonte, sem copiar regra entre redes |
| D-06 | Plano único por seleção | veda geração automática de variações |
| D-07 | Pendências e necessidades de inspeção ficam no relatório, não no plano | o plano não pode afirmar publicação verificada |
| D-08 | Compatibilidade de Composition é validador próprio que delega a v1 primeiro | nenhum campo novo injetado na v1; sem diagnóstico duplicado |
| D-09 | Vídeos do catálogo não carregam campo de áudio | compatível com a política de entrega sem áudio; codec não é licença para criar faixa |
| D-10 | `evidence` de default interno aponta para **este documento** (§1.2) ou para caminhos de `platform/`, nunca para `marcas/**` | 1080×1350 não tem caminho de evidência fora de dado de marca; o núcleo pode citar o achado sem importar o dado do cliente |
| D-11 | `ruleContext` entra no plano, no schema e no relatório (valor ou `null`); ausência é a **chave omitida**, nunca `null` | §2.1.1 condiciona a aplicação de regras a algo que precisava sobreviver à serialização; `null` continuaria representando "não informado", e `null` explícito na entrada é erro de contrato |
| D-12 | O plano **não** ganha campo de duração nem de formato de arquivo; limites de duração são avaliados na compatibilidade com a Composition | duração pertence à Composition/BeatPlan (§6.1) e formato exige inspeção de arquivo, que nada nesta fatia faz — escrever o número no plano seria certificado fictício |
| D-13 | Indisponibilidade de fonte não rebaixa regra: `source` (URL, título, data, citação) fica; a tentativa de revalidação é registrada à parte (§2.2) | disponibilidade do site e procedência da regra são estados distintos; mudança de regra exige evidência nova, não um erro de rede |
| D-14 | `OutputCompatibilityReport` embute `compositionReport` e `planReport` inteiros, e `validateCompositionForOutputPlan` para a comparação quando algum dos dois é inválido | preserva a causa da falha sem duplicar em camada nova o diagnóstico que o validador de projeto/composição já emitiu |
| D-15 | Uma única função avaliadora (`assessProfileRules`) parametrizada pelo **escopo da camada** (`output-plan` × `composition-output`), sem `if` por rede, perfil ou marca | o erro de duração só pode nascer onde o dado existe (soma declarada de cenas); na camada de saída o mesmo escopo silencia o que o `planReport` embutido já cobriu. Sem o parâmetro, a alternativa seria duplicar diagnóstico ou ramificar por nome de rede |
| D-16 | Comparação de preset é **igualdade estrita do token declarado**: `18:32` não vale como `9:16`, `0:0` é rejeitado | normalizar proporção exigiria coerção aritmética dentro do validador, e o plano passaria a afirmar uma forma que não declarou. A forma `W:H` continua aceita pelo schema — quem recusa é a relação semântica com o preset (§6.4), e o corpus separa os dois grupos |
| D-17 | O **estado da referência** (`informational`, `not-evaluated`) é verificado antes do gate de contexto | estado é fato da aplicação perfil↔regra certificado na R001-02; declarar um contexto não pode promover informação a exigência, nem rebaixar `not-evaluated` a erro |
| D-18 | `pendingRuleIds` e `requiresInspection` são ecoados sempre que o **perfil** resolve, ainda que o manifesto seja inválido | são fatos do catálogo sobre o perfil nomeado pelo plano, não relações com o projeto; omiti-los faria o relatório esconder uma pendência que existe |
| D-19 | Escopo de regra oficial é **lista de contextos** (`contexts: readonly RuleContext[]`) certificada pela mesma fonte, e o avaliador decide por `contexts.includes(contextoDeclarado)` | a fonte de Shorts diz "Você pode enviar Shorts de até três minutos pelo app YouTube e pelo YouTube Studio": com um contexto único, a alternativa seria duplicar `R-YT-01` (dois números para um limite) ou escolher um caminho e negar o outro. Lista é dado declarativo — não cria tabela paralela de limites nem `if` por rede/perfil. Escopo vazio é proibido: "nenhuma aplicação" é pendência de fonte, não regra |
| D-20 | Mudar **só o escopo** de uma regra sobe a revisão do perfil que a instancia (`youtube-shorts` 1 → 2) e atualiza a procedência (`quote` literal + `accessedOn` da revalidação); `PendingSourceRule.context` continua singular e anulado, e a separação app/API do Instagram não é tocada | §5 define revisão como o número que muda quando as regras do perfil mudam — escopo é parte da regra. Revalidar é decisão com evidência (D-13), não conveniência: a citação nova está na própria fonte. Pendência não tem aplicação certificada, então não tem escopo; `R-IG-01` segue `api-publishing` e `R-IG-04`/`R-IG-05` seguem `in-app`+`informational` |
| D-21 | Em `--json`, o stdout do plano é **exatamente** `resolution.plan`; avisos, códigos por camada, `pendencias de fonte:` e `requer inspecao:` vão para stderr **inclusive no sucesso** | separar "o que é artefato" de "o que ainda não pode ser certificado": no stdout misturado, nenhum consumidor releria o plano sem edição, e no silêncio total uma pendência de fonte viraria invisível justo no caminho feliz |
| D-22 | Listagem **sem** `--project` marca `availability: "not-consulted"`, nunca `"allowed"` | permissão é fato do manifesto do projeto, não do catálogo; omitir o manifesto não é autorização, e "habilitado" impresso sem consulta seria a primeira mentira da ferramenta mais lida |
| D-23 | Manifesto estruturalmente inválido **não** suprime a listagem: a lista filtrada sai com `blocked` + `OUTPUT_PROJECT_INVALID` em cada perfil, os issues do validador em `diagnostics`/stderr, e exit **1** | o erro de manifesto não apaga informação do catálogo; a lista bloqueada é justamente o que permite corrigir o `outputProfiles` sem adivinhar qual perfil o consumidor procurava |
| D-24 | A verificação opcional de Composition acontece **antes** de emitir o plano, e a falha deixa o stdout **vazio nos dois modos** (JSON e humano) | imprimir um plano recém-resolvido cuja composição já se sabe incompatível criaria um artefato que o próprio processo acabou de refutar. O desvio deliberado das CLIs antigas é este: `validate-composition-cli.ts:116-121` imprime o **relatório** no stdout mesmo com exit 1, porque o relatório é o resultado daquele contrato; aqui o resultado é o **plano**, e plano inexistente ou incompatível não tem artefato para imprimir — o que existe é diagnóstico em camadas no stderr (que, sim, continua como no erro de uso exit 2 das CLIs antigas) |
| D-25 | Camada compartilhada `platform/src/cli-input.ts` (parse de flags, enums, leitura de JSON, exit codes) em vez de copiar o parse por CLI — e **nenhum dicionário de formatos** nela: lista de `listOutputProfiles`, allowlist de `projectAllowedProfiles`, códigos estáveis do contrato do plano | duas CLIs com parse divergente virariam dois contratos; e o motivo de existir da R001 é ser a fonte única — reimplementar `FORMATS`/`sizes`/`hyperframes.json` na camada de CLI recriaria exatamente a concorrência registrada em §1.2 |
| D-26 | O manifesto técnico de demonstração **reusa** `id: "marca-salao"` e lista `vertical-social`, com teste que prova a aceitação da composição antiga **antes** do teste de divergência | `validateComposition` exige `composition.projectId === project.id`: sem reuso do ID, a única forma de demonstrar `OUTPUT_COMPAT_PROFILE_MISMATCH` seria editar ou substituir o exemplo oficial. Provar a aceitação primeiro é o que separa "o núcleo rejeitou a composição" de "o plano divergiu dela" |
| D-27 | Os cinco fixtures de `examples/output-plans/` foram **gerados pelo stdout da CLI** e o teste compara os bytes com uma execução nova (e relê cada um por ajv + `validateOutputPlan`) | exemplo digitado à mão vira tabela paralela no dia em que o catálogo mudar de novo; exemplo gravado da saída é revérificado a cada execução da suíte |
| D-28 | Pendência promovida é **apagada do registro**, não marcada como "resolvida"; o histórico da promoção mora em §2.2.1 deste documento | `PendingSourceRule` é ausência tipada (sem `value`, `source` nem `evidence`). Um estado "resolvida" criaria uma segunda fonte de verdade e deixaria espaço para um perfil ainda referenciar uma pendência que não existe mais. A prova de que a promoção foi deliberada é a citação + a tabela desta seção, e revisor humano continua necessário (D-13) |
| D-29 | Promover **não** é promover tudo o que a página diz: `value` só quando a fonte certifica um número ou uma forma única. Faixa de proporção, faixa de frame rate, peso de arquivo, bitrate, duração mínima, lista aberta de contêineres e condição de conta ficam **sem `value`** | `assessRuleValue` produziria erro de plano que a fonte não sustenta. Preferido: regra aplicada e não avaliável (`OUTPUT_PLAN_RULE_NOT_ASSESSABLE`), que diz "a regra alcança este perfil, o documento não traz o dado". O caminho alternativo — crescer a união `RuleValue` — mudaria o contrato para acomodar conteúdo, e o contrato é o que os artefatos antigos relêem |
| D-30 | Toda citação nova saiu da locale **`en`**, e o defeito de tradução da variante pt-BR fica **registrado na `note`** com as duas strings, sob teste | a Meta/Google declaram tradução automática nas variantes pt-BR, e nesta etapa a Stories API imprimiu "3 a 9 segundos" para "3 to 90 seconds". Sem a string errada no registro, a próxima leitura "limpa" o defeito e reintroduz um limite nove vezes mais estrito como se fosse o oficial |
| D-31 | Contradição dentro da mesma página: promove-se o **teto estrito** e registram-se os **dois** números; divergência entre páginas de objetos diferentes deixa a regra **sem `value`** | `R-FB-03` (60 s × 90 s na mesma página) — nenhuma das duas autoriza um story de 90 s. `R-FB-08` (9×16 × "9x16, 16x9" em páginas de objetos distintos) — fechar uma lista afirmaria exclusividade que a fonte não declara. Escolher o número conveniente silenciosamente é o que separa catálogo de palpites |
| D-32 | Pendência **estreitada** quando só parte foi certificada (`P-FB-01`), e **nova** pendência nomeada quando a leitura abre pergunta que antes não tinha ID (`P-FB-03` bytes de vídeo, `P-YT-03` contêiner/peso de Short) | apagar `P-FB-01` porque os formatos saíram certificados escondceria que a dimensão de foto continua sem fonte; e "a pergunta que eu ainda não tinha feito" não é "não há risco". O total foi de 10 → 4, não 10 → 0 |
| D-33 | `CATALOG_VERSION` continua `'1'`; a invalidação de artefatos obsoletos é feita por **`revision` por perfil** (11 perfis 1 → 2, `youtube-shorts` 2 → 3) | versão de contrato ≠ conteúdo da tabela. Um bump de contrato quebraria todo plano antigo, inclusive os de perfis cuja evidência não mudou; a revisão por perfil já produz `OUTPUT_PLAN_PROFILE_REVISION_INVALID`/`..._MISMATCH` exatamente onde a procedência do perfil mudou |
| D-34 | Cadência e cota **não** entram como regra avaliável; a que era o núcleo da pergunta promovida vira `PolicyNote` (`PN-YT-02`) | 100 posts/24 h, 400 contêineres/24 h, 30 Reels/24 h e 100 uploads/dia são fatos de **conta e agenda**, e o núcleo não autentica nem publica. Um campo de cota no OutputPlan seria certificado fictício — e o número antigo (as ~1600 unidades de custo de upload, substituídas por ~100 na mudança de 2025-12-04 registrada em `S-YT-QUOTA`) já está obsoleto, o que mostra o custo de tratar política como limite |

## 15. Não é escopo desta fatia (nem desta R001)

Frontend ou interface central; renderizador; integração de publicação; carrossel; migração geral de contratos; geração automática de variações; qualquer mudança nos fluxos de produção aprovados (inclusive a arte quadrada compartilhada e a exigência de autorização para Stories); criar rascunho, publicar ou agendar; gerar imagem, áudio ou vídeo; alterar a NS-001; mexer no Node global; versionar saídas temporárias; credencial em diff; push para `main`; merge da PR #7 ou de trabalho alheio.

## 16. O que o pacote afirmou × o que esta execução encontrou

Esta seção existia como "correções ao enunciado do pacote". A revisão da R001-01 mostrou que **as duas correções que ela listava não eram correções do pacote, e sim atribuições erradas deste documento**, porque a redação original citou `720×1280` e `meta.json` como se o pacote os houvesse escrito. O pacote (arquivo `Prompts-R001-Formatos-Instagram-Facebook-YouTube.md`, lido em 07/11/2026 UTC) **não contém** a string `720` nem a string `meta.json`; ele enuncia em "Decisões deste pacote" exatamente os quatro defaults `1080 × 1080, 1080 × 1350, 1080 × 1920 e 1920 × 1080` e, em "Referências verificadas", os templates `story_reel_vertical` e `youtube_horizontal`. Verificado com `grep -c` no anexo do titular (arquivo `Prompts-R001-Formatos-Instagram-Facebook-YouTube.md`, 17 932 bytes, 185 linhas — **não** está no repositório, então a conferência só é reproduzível com o arquivo em mãos), medido nesta execução: `720` → 0, `meta.json` → 0, `story_reel_vertical` → 2 linhas, `youtube_horizontal` → 2 linhas, `1080` → 2 linhas, `1350` → 2 linhas; a linha 28 do arquivo enuncia exatamente os quatro defaults `1080 × 1080, 1080 × 1350, 1080 × 1920 e 1920 × 1080` e a linha 39 lista os dois templates. Nada do que o pacote afirmou sobre geometria ou templates precisou ser corrigido.

Correção registrada (atribuição falsa desta etapa):
1. **720×1280 não veio do pacote.** Veio da fonte oficial: é o *mínimo* listado na página de compartilhamento de Stories **do app** (`S-IG-STORY`), e aparece também em documentação de vendors sob `.agents/skills/**`, fora de escopo. Dentro deste repositório a string não ocorre em `platform/`, `templates/`, `tools/` nem `marcas/`, então **não é default interno deste repositório** — conclusão que segue válida; o que estava errado era dizer que o pacote a havia citado.
2. **`meta.json` não foi citado pelo pacote.** A observação sobre onde a geometria dos templates mora é **achado adicional desta execução**, não refutação de algo dito.

Achados adicionais desta execução (nem confirmação nem refutação do enunciado):
- **A geometria dos templates não está nos `meta.json`.** Ela mora em `index.html`/`hyperframes.json` (§1.2). O pacote dizia apenas que os templates existem, e isso é verdade.
- **Existe um terceiro template** não listado no pacote: `reel_link_overlay` (1080×1920, fps 30, duração 27). Deve ser considerado ao mapear Reels em R001-04.
- **O HTTP 429 da Meta não persistiu.** O pacote registrou indisponibilidade ao abrir a página de publicação; a leitura desta etapa conseguiu o conteúdo pelo navegador. As duas experiências coexistem (a revisão da R001-01 voltou a encontrar 429/indisponibilidade no acesso direto), então **a rota de acesso é instável, não a informação**: as regras da Meta entraram com fonte e contexto, e as lacunas restantes continuam nomeadas em §2.2.
- **Os quatro defaults do pacote batem com o repositório**, mas com uma assimetria de proveniência: `1080×1080`, `1080×1920` e `1920×1080` têm evidência em caminhos técnicos; `1080×1350` só aparece em dado de marca (§1.2). Daí a decisão D-10.
- **(R001-05) "Facebook sem fonte" era "Facebook com uma página só tentada".** A R001-02 registrou `P-FB-01` como "não consultado com sucesso" com base em `docs/video-api/`, que de fato só aponta para "Reference". As páginas específicas (`graph-api/reference/page/photos/`, `video-api/page-stories-api`, `video-api/guides/reels-publishing`) abriram e certificaram nove regras. O enunciado do pacote não dizia nada sobre o Facebook, e continua não dizendo: a correção é deste documento, não do pacote.
- **(R001-05) o pacote pediu "formatos oficiais"; os oficiais vêm em camadas.** Duração, geometria e formato têm fonte primária; peso, bitrate, cadência e cota também, mas não são verificáveis por um plano que não abre arquivo nem autentica. Registrar os segundos como se fossem os primeiros é o erro que a separação `applies` × `value` existe para impedir (D-29).
