# Platform — núcleo modular da Content Factory

Esta pasta contém as fatias implementadas do núcleo modular previsto em
[`docs/decisoes/MKT-VIDEO-001-producao-modular.md`](../docs/decisoes/MKT-VIDEO-001-producao-modular.md),
[`docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md`](../docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md)
e [`docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md`](../docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md):

1. **Primeira fatia** — Manifesto de projeto → validação → relatório estruturado → testes com dois projetos diferentes.
2. **Segunda fatia** — Composition v1 → vínculo entre projeto e composição → validação → relatório estruturado → CLI → testes com dois projetos.
3. **Terceira fatia** — BeatPlan v1 → tradução temporal da Composition em beats ordenados → vínculo com projeto e composição → validação temporal → relatório estruturado → CLI → testes com dois projetos.

> “Marca Salão será o primeiro consumidor da plataforma, não o núcleo da plataforma.”

## O que é o ProjectManifest

É um **manifesto declarativo** (`*.project.json`) que descreve um projeto consumidor da
Content Factory: identidade, idioma, fuso, tema visual, raiz de assets, políticas editoriais
explícitas e profiles de saída. Ele é **dado**, não código: o núcleo não interpreta
`brandTheme`, `locale`, `outputProfiles` ou as políticas — apenas exige que estejam bem
formados, com o mesmo validador para qualquer projeto.

## Core × projeto

| Núcleo (`platform/src`, `platform/schemas`) | Projeto consumidor (`platform/examples/projects`) |
|---|---|
| Contrato, schema e validador genéricos | Dados concretos: marca, idioma, tema, assets, políticas |
| Não conhece nenhum projeto específico | Deve seguir o contrato; pode ter qualquer valor válido |
| Zero regra comercial | Regras editoriais declaradas como booleanos explícitos |

## Campos do manifesto

| Campo | Regra |
|---|---|
| `schemaVersion` | Inteiro `1` (única versão suportada) |
| `id` | Obrigatório, kebab-case |
| `name` | Obrigatório, não vazio (opaco ao núcleo) |
| `locale` | Obrigatório (opaco ao núcleo) |
| `timezone` | Obrigatório (opaco ao núcleo) |
| `brandTheme` | Obrigatório e **opaco ao núcleo** |
| `assetRoot` | Caminho **relativo seguro**: sem absoluto, sem `..`, sem arquivos sensíveis |
| `contentPolicies` | Objeto com exatamente 4 booleanos explícitos (ausência é erro, não default) |
| `outputProfiles` | Array não vazio, itens em kebab-case, sem duplicatas |
| campos desconhecidos | **Proibidos** no topo e em `contentPolicies` (`additionalProperties: false`) |

## Códigos de validação (estáveis)

`PROJECT_MANIFEST_INVALID`, `PROJECT_SCHEMA_VERSION_UNSUPPORTED`, `PROJECT_ID_REQUIRED`,
`PROJECT_ID_INVALID`, `PROJECT_NAME_REQUIRED`, `PROJECT_LOCALE_REQUIRED`,
`PROJECT_TIMEZONE_REQUIRED`, `PROJECT_BRAND_THEME_REQUIRED`, `PROJECT_ASSET_ROOT_REQUIRED`,
`PROJECT_ASSET_ROOT_ABSOLUTE`, `PROJECT_ASSET_ROOT_TRAVERSAL`, `PROJECT_ASSET_ROOT_SENSITIVE`,
`PROJECT_CONTENT_POLICY_INVALID`, `PROJECT_OUTPUT_PROFILE_REQUIRED`,
`PROJECT_OUTPUT_PROFILE_INVALID`, `PROJECT_OUTPUT_PROFILE_DUPLICATE`, `PROJECT_UNKNOWN_FIELD`.

O validador coleta **todos** os erros relevantes (não só o primeiro), em ordem de emissão
fixa e determinística. A automação deve confiar nos códigos, não nas mensagens livres.

## Formato do relatório

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "summary": "Project manifest is valid.",
  "projectId": "marca-salao",
  "schemaVersion": 1,
  "outputProfileCount": 1
}
```

Determinístico: sem timestamp, sem caminhos absolutos da máquina, sem IDs aleatórios.
`warnings` existe para evolução futura e hoje é sempre `[]`.

## O que é a Composition v1

É um **contrato declarativo** (`*.composition.json`) que descreve uma peça em cenas:
formato de saída, cenas com texto canônico ou referências de assets, adaptador de
renderização e metadata técnica. Ela **não é roteiro, não é BeatPlan e não é
renderização**: não existem beats executáveis, áudio, prompts, providers, hashes,
licenças, montagem nem geração de assets nesta fatia. Assets são **referenciados, não
gerados**, e a existência física não é verificada. O texto canônico permanece
estruturado e editável fora de imagens e vídeos.

## Campos da composição

| Campo | Regra |
|---|---|
| `schemaVersion` | Inteiro `1` (única versão suportada) |
| `projectId` | Obrigatório, kebab-case; deve ser igual a `project.id` |
| `id` | Obrigatório, kebab-case |
| `title` | Obrigatório, não vazio (opaco ao núcleo) |
| `locale` | Obrigatório; na v1 deve ser **igual** a `project.locale` |
| `format` | Objeto com `profile` (kebab-case, presente em `project.outputProfiles`), `width` e `height` inteiros positivos e `fps` inteiro entre 1 e 120 |
| `scenes` | Array de cenas: `id` kebab-case único, `type` em `text`/`image`/`video`/`cta`, `durationMs` inteiro > 0 e `content` em forma fechada por tipo |
| `renderer` | Objeto com `adapter` kebab-case obrigatório; `undecided` é aceito e nenhum adapter precisa estar instalado; `options` não é suportado na v1 |
| `metadata` | Opcional e pequeno: `status` em `draft`/`review`/`approved`/`archived`, `description` e `tags` (strings sem duplicata, no máximo 8) |
| campos desconhecidos | **Proibidos** no topo, em `format`, em cada cena, em `content`, em `asset`, em `renderer` e em `metadata` |

`content` por tipo: `text` exige `text` e proíbe `asset`; `cta` exige `text` e aceita
`href` somente http(s) sem credenciais embutidas (a URL nunca é acessada); `image` e
`video` exigem `asset` e aceitam `alt`. `accessibilityLabel` é opcional em todos.

## AssetReference mínimo

`asset` tem somente `id` (kebab-case) e `path` (caminho relativo seguro: sem absoluto,
sem `..`, sem URL/protocolo, sem credenciais e sem arquivos sensíveis). **AssetReference
não substitui o futuro AssetManifest**: hash, licença, origem, provider, prompt,
dimensões e duração pertencem a uma fatia futura.

## Metadata técnica ≠ autorização editorial

`metadata.status: "approved"` é um estado **técnico** do artefato declarativo. Ele não
concede autorização editorial, de gravação ou de publicação: essas autorizações
continuam regidas por `AGENTS.md`, `WORKFLOW.md` e pelos briefings aprovados.

## Códigos de validação de composição (estáveis)

`COMPOSITION_INVALID`, `COMPOSITION_MANIFEST_INVALID`, `COMPOSITION_UNKNOWN_FIELD`,
`COMPOSITION_SCHEMA_VERSION_UNSUPPORTED`, `COMPOSITION_PROJECT_ID_REQUIRED`,
`COMPOSITION_PROJECT_ID_INVALID`, `COMPOSITION_PROJECT_ID_MISMATCH`, `COMPOSITION_ID_REQUIRED`,
`COMPOSITION_ID_INVALID`, `COMPOSITION_TITLE_REQUIRED`, `COMPOSITION_LOCALE_REQUIRED`,
`COMPOSITION_LOCALE_MISMATCH`, `COMPOSITION_FORMAT_REQUIRED`,
`COMPOSITION_FORMAT_PROFILE_REQUIRED`, `COMPOSITION_FORMAT_PROFILE_INVALID`,
`COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED`, `COMPOSITION_FORMAT_WIDTH_INVALID`,
`COMPOSITION_FORMAT_HEIGHT_INVALID`, `COMPOSITION_FORMAT_FPS_INVALID`,
`COMPOSITION_SCENE_REQUIRED`, `COMPOSITION_SCENE_INVALID`, `COMPOSITION_SCENE_ID_REQUIRED`,
`COMPOSITION_SCENE_ID_INVALID`, `COMPOSITION_SCENE_ID_DUPLICATE`, `COMPOSITION_SCENE_TYPE_INVALID`,
`COMPOSITION_SCENE_DURATION_INVALID`, `COMPOSITION_SCENE_CONTENT_REQUIRED`,
`COMPOSITION_SCENE_CONTENT_FIELD_FORBIDDEN`, `COMPOSITION_TEXT_REQUIRED`,
`COMPOSITION_ASSET_REQUIRED`, `COMPOSITION_ASSET_NOT_ALLOWED`, `COMPOSITION_ASSET_ID_INVALID`,
`COMPOSITION_ASSET_PATH_REQUIRED`, `COMPOSITION_ASSET_PATH_ABSOLUTE`,
`COMPOSITION_ASSET_PATH_TRAVERSAL`, `COMPOSITION_ASSET_PATH_SENSITIVE`,
`COMPOSITION_ASSET_PATH_URL`, `COMPOSITION_CTA_HREF_INVALID`,
`COMPOSITION_CTA_HREF_CREDENTIALS`, `COMPOSITION_RENDERER_REQUIRED`,
`COMPOSITION_RENDERER_ADAPTER_REQUIRED`, `COMPOSITION_RENDERER_ADAPTER_INVALID`,
`COMPOSITION_RENDERER_OPTIONS_UNSUPPORTED`, `COMPOSITION_METADATA_INVALID`,
`COMPOSITION_METADATA_STATUS_INVALID`, `COMPOSITION_METADATA_TAG_DUPLICATE`,
`COMPOSITION_DURATION_OVERFLOW`.

Ordem de emissão fixa: primeiro o manifesto do projeto, depois a estrutura da
composição, depois os vínculos entre os dois. A automação deve confiar nos códigos,
não nas mensagens livres.

## Warnings técnicos (heurísticas, não aprovação editorial)

`COMPOSITION_SCENE_TEXT_LONG` (texto de cena `text`/`cta` acima de 160 caracteres),
`COMPOSITION_SCENE_DURATION_SHORT` (cena com texto com `durationMs` abaixo de 1000) e
`COMPOSITION_RENDERER_UNDECIDED` (`renderer.adapter: "undecided"`). Warnings não tornam
a composição inválida (`valid` continua `true`), têm `code`, `path` e `message` e ordem
de emissão estável (ordem das cenas; renderer por último). Os limites são heurísticas
técnicas de legibilidade/duração: não substituem revisão editorial.

## Política de duração

`totalDurationMs` é a soma dos `durationMs` inteiros positivos das cenas. Cada valor
individual deve ser um inteiro seguro (> 0 e <= `Number.MAX_SAFE_INTEGER`); se a soma
ultrapassar `Number.MAX_SAFE_INTEGER`, o validador emite `COMPOSITION_DURATION_OVERFLOW`
e reporta `totalDurationMs: null` — nunca um número impreciso.

## Formato do relatório de composição

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "summary": "Composition is valid.",
  "projectId": "marca-salao",
  "compositionId": "pilot-composition",
  "schemaVersion": 1,
  "sceneCount": 3,
  "totalDurationMs": 10000,
  "format": {
    "profile": "vertical-social",
    "width": 1080,
    "height": 1920,
    "fps": 30
  },
  "rendererAdapter": "undecided"
}
```

`totalDurationMs` é a soma dos `durationMs` inteiros positivos das cenas. Determinístico:
sem timestamp, sem caminhos absolutos, sem IDs aleatórios, sem stack traces.

## O que é o BeatPlan v1

É a **tradução temporal** de uma Composition válida (`*.beat-plan.json`): uma lista
ordenada de beats com início, duração, função narrativa, texto e intenções visuais.

Três distinções que esta fatia registra expressamente:

- **BeatPlan não é roteiro.** O roteiro continua sendo a fonte editorial; o plano é a
  tradução temporal para produção.
- **BeatPlan não é Composition.** A Composition declara formato e cenas; o BeatPlan
  declara quando cada recorte acontece e o que ele cumpre narrativamente.
- **Cena e beat não possuem relação obrigatória de um para um.** Um beat pode
  atravessar mais de uma cena (quando declarado em `sceneIds`) e uma cena pode ser
  referenciada por mais de um beat, inclusive beats consecutivos.

O BeatPlan **não gera beats automaticamente**: esta fatia cria contrato, schema,
exemplos, validação, relatório, CLI e testes. Nenhum beat é derivado de roteiro, de
narração ou de cena por qualquer automática do núcleo.

## Campos do BeatPlan

| Campo | Regra |
|---|---|
| `schemaVersion` | Inteiro `1` (única versão suportada) |
| `projectId` | Obrigatório, kebab-case; deve ser igual a `project.id` |
| `compositionId` | Obrigatório, kebab-case; deve ser igual a `composition.id` |
| `id` | Obrigatório, kebab-case |
| `locale` | Obrigatório; deve ser igual a `project.locale` e a `composition.locale` |
| `beats` | Array **não vazio** de beats, na ordem do campo `order` |
| `metadata` | Opcional e pequeno: `status`, `description` e `tags` |
| campos desconhecidos | **Proibidos** no topo, em cada beat, em `narration` e em `metadata` |

## Campos do Beat

| Campo | Regra |
|---|---|
| `id` | Obrigatório, kebab-case, único no plano |
| `order` | Inteiro a partir de `1`, único, sequência contínua sem lacunas e igual à posição no array |
| `sceneIds` | Array não vazio, sem duplicações, cada id em kebab-case e **existente na Composition** |
| `narrativeFunction` | Um dos valores neutros listados abaixo |
| `startMs` | Inteiro seguro `>= 0` |
| `durationMs` | Inteiro seguro `> 0` |
| `narration` | Opcional; objeto com **somente** `text` não vazio |
| `onScreenText` | Opcional; string não vazia quando presente |
| `visualIntent` | Obrigatório; texto não vazio e declarativo |
| `motionIntent` | Um dos valores neutros listados abaixo |
| `transitionIn` / `transitionOut` | Um dos valores neutros listados abaixo |
| `editorialEvidence` | Array não vazio de strings não vazias, sem duplicações |
| `validationStatus` | `draft`, `review`, `validated` ou `rejected` |

`narration` **não é áudio**: é somente texto canônico. Não há provider, voz, arquivo,
configuração de TTS, nem qualquer campo além de `text`. O `AudioPlan` pertence a uma
fatia futura.

`onScreenText` permanece **texto canônico editável**, nunca incorporado a imagem:
correção de texto não exige regenerar visual.

`visualIntent` é **descritiva**: descreve intenção, não é prompt de fornecedor e não
deve conter configuração executável de ferramenta.

`motionIntent` **não executa movimento** e `transitionIn`/`transitionOut` **não executam
animação**: são intenções neutras que um futuro adaptador traduziria (ou degradaria de
forma registrada).

`editorialEvidence` guarda **identificadores conceituais**, sem duplicação, sem caminhos
absolutos, sem traversal e sem URLs. A **existência física não é verificada** nesta versão.

### Funções narrativas (neutras)

`hook`, `context`, `problem`, `demonstration`, `explanation`, `proof`, `transition`,
`cta`, `closing`. Nenhuma função específica de projeto consumidor pertence ao núcleo.

### Intenções de movimento (neutras)

`none`, `slow-zoom`, `parallax-depth`, `camera-orbit`, `pan`, `tilt`, `hold`.

### Intenções de transição (neutras)

`none`, `cut`, `fade`, `dissolve`, `slide`, `material-dissolve`.

## Política temporal da v1

A timeline é **estritamente linear**:

- o primeiro beat começa em `0`;
- os beats são contíguos, **sem lacunas** e **sem sobreposição**;
- `beat[n].startMs = beat[n-1].startMs + beat[n-1].durationMs`;
- o último beat termina **exatamente** na duração total da Composition;
- o array aparece na mesma ordem indicada pelo campo `order`.

Sobreposição, trilhas paralelas e lacunas intencionais ficam **fora da v1**.

O validador **não corrige** tempos, **não reordena** beats, **não preenche** lacunas,
**não corta** beats e **não altera** a Composition: ele apenas reporta.

`beatEndMs = startMs + durationMs` só é calculado depois de validar que `startMs` e
`durationMs` são inteiros seguros. Se alguma soma ultrapassar `Number.MAX_SAFE_INTEGER`,
o validador emite `BEAT_PLAN_DURATION_OVERFLOW`, **não retorna valor aproximado**,
interrompe as comparações temporais dependentes desse valor e reporta
`totalDurationMs: null`.

O tempo do beat **não é inferido** da duração individual da cena, e nenhuma referência
de cena é criada automaticamente por posição de array.

## Relação com cenas

`sceneIds` deve referenciar cenas existentes em `Composition.scenes`. BeatPlan v1 **não
exige** que todas as cenas sejam referenciadas: cada cena não referenciada gera o
warning `BEAT_PLAN_SCENE_UNREFERENCED`, em ordem estável seguindo a Composition.
`sceneId` inexistente é **erro** (`BEAT_PLAN_SCENE_NOT_FOUND`).

## Vínculo com ProjectManifest e Composition

A validação recebe os três documentos explicitamente — `validateBeatPlan(beatPlan,
composition, project)` — e confirma, nesta ordem: projeto válido; composição válida
para o projeto; BeatPlan estruturalmente válido; `projectId` igual a `project.id`;
`compositionId` igual a `composition.id`; `locale` igual ao do projeto e ao da
composição; `sceneIds` existentes; timeline válida; duração total igual à da
Composition.

Não há registry global, descoberta automática de arquivos, banco, API, acesso remoto ou
resolução por nome de marca. Se o `ProjectManifest` for inválido, emite-se
`BEAT_PLAN_PROJECT_MANIFEST_INVALID`. Se a Composition for inválida, emite-se
`BEAT_PLAN_COMPOSITION_INVALID` e a timeline **não** é comparada com uma duração não
confiável (`compositionDurationMs: null`).

## Metadata técnica ≠ autorização editorial

`metadata` aceita somente `status` (`draft`, `review`, `validated`, `archived`),
`description` e `tags` (no máximo 8, strings não vazias, sem duplicação). Campos
desconhecidos são rejeitados e `tags` não controlam lógica do core.

> `metadata.status: "validated"` significa apenas que o BeatPlan passou por validação
> **técnica** no pipeline.

Não significa briefing aprovado, hook aprovado, roteiro aprovado, autorização de
gravação, autorização de produção nem autorização de publicação. O mesmo vale para
`validationStatus: "validated"` em um beat: é revisão técnica, não concessão editorial.
Essas autorizações continuam regidas por `AGENTS.md`, `WORKFLOW.md` e pelos briefings
aprovados.

## Códigos de validação de BeatPlan (estáveis)

`BEAT_PLAN_MANIFEST_INVALID`, `BEAT_PLAN_SCHEMA_VERSION_UNSUPPORTED`, `BEAT_PLAN_UNKNOWN_FIELD`,
`BEAT_PLAN_PROJECT_MANIFEST_INVALID`, `BEAT_PLAN_COMPOSITION_INVALID`,
`BEAT_PLAN_PROJECT_ID_REQUIRED`, `BEAT_PLAN_PROJECT_ID_INVALID`, `BEAT_PLAN_PROJECT_ID_MISMATCH`,
`BEAT_PLAN_COMPOSITION_ID_REQUIRED`, `BEAT_PLAN_COMPOSITION_ID_INVALID`, `BEAT_PLAN_COMPOSITION_ID_MISMATCH`,
`BEAT_PLAN_ID_REQUIRED`, `BEAT_PLAN_ID_INVALID`, `BEAT_PLAN_LOCALE_REQUIRED`, `BEAT_PLAN_LOCALE_MISMATCH`,
`BEAT_PLAN_BEATS_REQUIRED`, `BEAT_PLAN_BEAT_INVALID`, `BEAT_PLAN_BEAT_ID_REQUIRED`,
`BEAT_PLAN_BEAT_ID_INVALID`, `BEAT_PLAN_BEAT_ID_DUPLICATE`, `BEAT_PLAN_ORDER_INVALID`,
`BEAT_PLAN_ORDER_DUPLICATE`, `BEAT_PLAN_ORDER_SEQUENCE_INVALID`, `BEAT_PLAN_ARRAY_ORDER_MISMATCH`,
`BEAT_PLAN_SCENE_IDS_REQUIRED`, `BEAT_PLAN_SCENE_ID_INVALID`, `BEAT_PLAN_SCENE_ID_DUPLICATE`,
`BEAT_PLAN_SCENE_NOT_FOUND`, `BEAT_PLAN_NARRATIVE_FUNCTION_INVALID`, `BEAT_PLAN_START_INVALID`,
`BEAT_PLAN_DURATION_INVALID`, `BEAT_PLAN_DURATION_OVERFLOW`, `BEAT_PLAN_TIMELINE_START_INVALID`,
`BEAT_PLAN_TIMELINE_GAP`, `BEAT_PLAN_TIMELINE_OVERLAP`, `BEAT_PLAN_TIMELINE_END_MISMATCH`,
`BEAT_PLAN_NARRATION_INVALID`, `BEAT_PLAN_NARRATION_TEXT_REQUIRED`,
`BEAT_PLAN_ON_SCREEN_TEXT_INVALID`, `BEAT_PLAN_VISUAL_INTENT_REQUIRED`,
`BEAT_PLAN_MOTION_INTENT_INVALID`, `BEAT_PLAN_TRANSITION_IN_INVALID`,
`BEAT_PLAN_TRANSITION_OUT_INVALID`, `BEAT_PLAN_EDITORIAL_EVIDENCE_REQUIRED`,
`BEAT_PLAN_EDITORIAL_EVIDENCE_INVALID`, `BEAT_PLAN_EDITORIAL_EVIDENCE_DUPLICATE`,
`BEAT_PLAN_VALIDATION_STATUS_INVALID`, `BEAT_PLAN_METADATA_INVALID`,
`BEAT_PLAN_METADATA_STATUS_INVALID`, `BEAT_PLAN_METADATA_DESCRIPTION_INVALID`,
`BEAT_PLAN_METADATA_TAG_INVALID`, `BEAT_PLAN_METADATA_TAG_DUPLICATE`, `BEAT_PLAN_METADATA_TAG_LIMIT`.

Ordem de emissão fixa: primeiro o manifesto do projeto, depois a composição, depois a
estrutura do plano (campos de topo, beats em ordem de array, `order` e `metadata`),
depois os vínculos entre os três, depois a relação com as cenas e por último a timeline
(início em zero, lacuna/sobreposição e término). A automação deve confiar nos códigos,
não nas mensagens livres.

`BEAT_PLAN_LOCALE_MISMATCH` é emitido **uma única vez** por plano: como a Composition
válida já garante `composition.locale == project.locale`, reportar os dois vínculos
separadamente duplicaria o mesmo erro sem diferença semântica.

## Warnings técnicos de BeatPlan (heurísticas, não aprovação editorial)

| Código | Quando |
|---|---|
| `BEAT_PLAN_NARRATION_MISSING` | Nenhum beat declara `narration` (emitido uma vez) |
| `BEAT_PLAN_ON_SCREEN_TEXT_MISSING` | Nenhum beat declara `onScreenText` (emitido uma vez) |
| `BEAT_PLAN_NARRATION_TEXT_LONG` | `narration.text` acima de 240 caracteres |
| `BEAT_PLAN_ON_SCREEN_TEXT_LONG` | `onScreenText` acima de 160 caracteres |
| `BEAT_PLAN_READING_TIME_RISK` | `durationMs` menor que o tempo mínimo estimado de leitura do `onScreenText` |
| `BEAT_PLAN_SCENE_UNREFERENCED` | Cena da Composition não referenciada por nenhum beat (uma por cena) |

Peças sem narração e peças sem texto de tela **são permitidas**: os dois primeiros
warnings são informativos. Nenhum warning torna `valid` falso.

Ordem estável dos warnings: (1) globais, (2) por beat seguindo a ordem do array,
(3) cenas não referenciadas seguindo a ordem da Composition. Warnings são calculados
somente quando `beats` é um array não vazio; `BEAT_PLAN_SCENE_UNREFERENCED` exige
Composition confiável.

### Heurística de tempo de leitura

```text
wordCount                 = quantidade de palavras após trim, separadas por espaço
estimatedMinimumReadingMs = max(1000, wordCount * 300)
```

O cálculo é determinístico: espaços repetidos não contam como palavras extras, pontuação
não exige parser linguístico e não há arredondamento instável. Texto vazio já é **erro**
(`BEAT_PLAN_ON_SCREEN_TEXT_INVALID`), não warning. O warning informa a duração disponível
e a duração mínima estimada.

A heurística **não é aprovação editorial**: não substitui leitura humana cronometrada e
não considera complexidade semântica, fonte, contraste nem público. Funciona apenas como
alerta técnico inicial.

## Formato do relatório de BeatPlan

```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "summary": "Beat plan is valid.",
  "projectId": "marca-salao",
  "compositionId": "pilot-composition",
  "beatPlanId": "pilot-beat-plan",
  "schemaVersion": 1,
  "beatCount": 4,
  "compositionSceneCount": 3,
  "referencedSceneCount": 3,
  "totalDurationMs": 10000,
  "compositionDurationMs": 10000,
  "narrationBeatCount": 4,
  "onScreenTextBeatCount": 4,
  "metadataStatus": "draft"
}
```

Política dos campos derivados:

- `beatCount` conta as entradas de `beats` que **são objetos JSON** (contagem
  estrutural; `0` quando `beats` está ausente ou malformado). Um plano inválido pode ter
  `beatCount > 0`: a contagem não implica beats válidos.
- `compositionSceneCount` e `compositionDurationMs` vêm da Composition **válida**; ficam
  `0` e `null` quando a Composition não é confiável.
- `referencedSceneCount` conta `sceneIds` **únicos e existentes**; ids inexistentes são
  erro e não entram na contagem.
- `totalDurationMs` é a soma segura dos `durationMs` dos beats; `null` em overflow.
- `narrationBeatCount` e `onScreenTextBeatCount` contam beats com `narration` e
  `onScreenText` **bem formados**.
- `metadataStatus` ecoa o status declarado e válido; `null` quando ausente ou inválido.

`summary` é estável: `Beat plan is valid.` ou `Beat plan is invalid: N error(s).`
Warnings **não** entram na contagem de errors. Determinístico: sem timestamp, sem caminho
absoluto da máquina, sem ID aleatório, sem stack trace, sem conteúdo de arquivo de
ambiente e sem mutação de input.

## Exemplos de BeatPlan

`examples/beat-plans/marca-salao-pilot.beat-plan.json` (pt-BR, 4 beats, 10000 ms) e
`examples/beat-plans/fixture-project-pilot.beat-plan.json` (en-US, 2 beats, 5000 ms)
passam pelo **mesmo** validador, sem condicional por projeto. O exemplo do Marca Salão
demonstra a relação não 1:1: `demo-frame` é referenciada por dois beats e um beat
atravessa `demo-frame` e `closing`. O exemplo fixture demonstra que `narration` pode
estar ausente em um beat e presente em outro.

Ambos são **fixtures de contrato com conteúdo técnico**: não copiam a NS-001, não usam
conteúdo promocional real, não referenciam mídia física e **não são peças aprovadas**.

## Como executar

Requisito: **Node >= 22** (runtime mínimo, declarado em `engines`: `>=22 <25`). O
TypeScript é **compilado para JavaScript antes da execução** (`tsc` → `dist/`); nenhuma
execução direta de `.ts` é necessária. Zero dependências de runtime.

```bash
# a partir de platform/
npm ci                    # instala as devDependencies (typescript, @types/node)
npm run clean             # apaga dist/ (script Node portátil)
npm run build             # compila src/ e tests/ para dist/ (tsc, NodeNext)
npm run typecheck         # tsc --noEmit
npm test                  # build + node --test dist/tests/*.test.js (JavaScript compilado)

# CLI compilada (exit 0 válido · 1 manifesto inválido · 2 uso/JSON malformado)
npm run content:validate-project -- --project examples/projects/marca-salao.project.json --json
npm run content:validate-project -- --project examples/projects/fixture-project.project.json

# CLI de composicao (exit 0 válida · 1 inválida · 2 uso/JSON malformado)
npm run content:validate-composition -- --project examples/projects/marca-salao.project.json --composition examples/compositions/marca-salao-pilot.composition.json --json
npm run content:validate-composition -- --project examples/projects/fixture-project.project.json --composition examples/compositions/fixture-project-pilot.composition.json

# CLI de beat plan (exit 0 válido · 1 inválido · 2 uso/JSON malformado)
npm run content:validate-beat-plan -- --project examples/projects/marca-salao.project.json --composition examples/compositions/marca-salao-pilot.composition.json --beat-plan examples/beat-plans/marca-salao-pilot.beat-plan.json --json
npm run content:validate-beat-plan -- --project examples/projects/fixture-project.project.json --composition examples/compositions/fixture-project-pilot.composition.json --beat-plan examples/beat-plans/fixture-project-pilot.beat-plan.json
```

`dist/` é **artefato local** gerado pelo build e está ignorado pelo Git
(`platform/.gitignore`). Os exemplos JSON continuam sendo lidos da árvore-fonte
(`platform/examples/projects/`, `platform/examples/compositions/` e
`platform/examples/beat-plans/`); o caminho informado em `--project`, `--composition` e
`--beat-plan` é resolvido em relação ao diretório atual de execução.

Exit codes da CLI: `0` válido · `1` documento semanticamente inválido (relatório
emitido) · `2` erro de uso, arquivo inexistente ou JSON malformado (mensagem sanitizada,
sem stack trace). Na CLI de beat plan, `1` cobre ProjectManifest, Composition ou BeatPlan
inválidos; `2` cobre ausência ou JSON malformado de qualquer um dos três arquivos. As
três CLIs leem **somente** os arquivos informados, não acessam rede, não abrem assets,
não alteram os inputs, não criam outputs, não geram mídia e não leem `.env`.

O **Node 22** é o runtime homologado (`engines: >=22 <25`); o TypeScript é sempre
compilado para `dist/` antes da execução e nenhuma CLI executa `.ts` diretamente.

## Como adicionar um novo projeto

1. Copie um exemplo para um novo `*.project.json`;
2. Troque `id`, `name`, `locale`, `timezone`, `brandTheme`, `assetRoot`, políticas e
   `outputProfiles` para os valores do novo projeto;
3. Valide com a CLI (exit 0 esperado);
4. Nenhuma mudança no núcleo é necessária — se for, o contrato está sendo violado.

## Segurança de caminhos

`assetRoot` rejeita caminhos absolutos (POSIX, letra de unidade e UNC), qualquer segmento
`..` e referências a arquivos sensíveis (`.env`, chaves privadas, `*.pem`/`*.key`,
credenciais, `service_account`, secrets, `.git`). A CLI lê **somente** o arquivo informado,
não acessa rede, não altera arquivos, não cria outputs e não lê `.env`.
A **existência física** de assets não é verificada nesta fatia (fora de escopo).

## Stack e dependências

- TypeScript com sintaxe erasable (sem enums/namespaces), **compilado com `tsc` antes
  da execução** (ESM/NodeNext, target ES2022, saída em `dist/`) — **zero dependências
  de runtime**;
- Validações explícitas escritas à mão (superfície pequena e enumerada); os arquivos
  `schemas/project.schema.json`, `schemas/composition.schema.json` e
  `schemas/beat-plan.schema.json` (JSON Schema draft-07) são a descrição normativa dos
  contratos e espelham os validadores, testados por suas suítes em `tests/` (além dos
  testes de portabilidade do build). Regras entre documentos — vínculos de id/locale,
  existência de `sceneIds`, timeline contígua e duração total — **não** são expressáveis
  em JSON Schema e vivem somente nos validadores;
- `node:test` nativo para os testes, executados sobre o JavaScript compilado em
  `dist/tests`;
- DevDependencies apenas para o gate de tipos e o build, fixadas: `typescript@5.9.3`
  (Apache-2.0) e `@types/node@24.19.2` (MIT). Nenhum pacote de vídeo, parser YAML ou
  JSON Schema runtime foi adicionado; nenhuma dependência foi adicionada nesta fatia.

## Limites atuais (expressos)

- **Composition v1 implementada apenas como contrato declarativo** (sem áudio, prompts,
  providers, montagem, timeline executável ou geração de assets);
- **BeatPlan v1 implementado apenas como contrato declarativo** e **não gera beats
  automaticamente**: nenhum beat é derivado de roteiro, de narração, de cena ou de
  estimativa automática de fala;
- **`narration` não é áudio** — é somente texto canônico. **Não há TTS**, **não há
  arquivo de narração**, **não há provider**, não há voz e não há configuração de áudio;
- **`motionIntent` não executa movimento** e as **transições não executam animação**:
  descrevem intenção, nada mais;
- **Nenhuma renderização** existe: nem preview, nem render, nem upload, nem publicação;
- **Nenhum AssetManifest** (além do `AssetReference` mínimo da Composition), **nenhum
  AudioPlan**, **nenhum RenderPlan**, **nenhum VisualStyle**, **nenhum VisualAnchor** e
  **nenhum adaptador** foi implementado nesta fatia;
- **Nenhum renderizador foi implementado** (HTML/edição: nada adotado;
  `renderer.adapter: "undecided"` é aceito e nenhum adapter precisa estar instalado);
- **HyperFrames não foi instalado** e permanece apenas possibilidade futura atrás de adaptador;
- **Nenhum vídeo é gerado** e nenhum preview/render/upload/publicação existe;
- **Nenhuma ferramenta audiovisual externa foi instalada** por estas fatias (HyperFrames,
  Google Flow, ElevenLabs, FFmpeg, CapCut etc. permanecem não adotados);
- **Zero dependências de runtime**: nenhuma biblioteca de timeline, validação de schema,
  YAML, parser linguístico, TTS, áudio, mídia, vídeo, cliente HTTP ou SDK de fornecedor
  foi adicionada;
- A timeline da v1 é **somente linear**: sobreposição, trilhas paralelas e lacunas
  intencionais ficam fora;
- Os **exemplos não autorizam publicação** — são fixtures de contrato, não campanhas;
- **`validationStatus: "validated"` não autoriza publicação** e
  **`metadata.status: "validated"` não autoriza publicação**: ambos são estados técnicos;
- **NS-001 não foi migrada nem alterada** e nenhuma campanha/briefing/hook/roteiro foi tocado;
- **Marca Salão é consumidor, não núcleo** — `platform/src` e `platform/schemas` não
  contêm referência a ele (há teste estrutural que garante isso a cada execução).

## Próximos incrementos possíveis (não compromissos)

- Evolução do pipeline após o BeatPlan (VisualStyle, VisualAnchor, AssetManifest
  completo, AudioPlan, RenderPlan);
- Timeline não linear (sobreposição, trilhas paralelas e lacunas intencionais), hoje
  fora da v1 do BeatPlan;
- Validator editorial (briefing/roteiro aprovados) e de assets;
- Adaptadores de renderizador (HTML/CSS como primeiro candidato);
- Preview e renderização reproduzíveis; inspeção e report de artefatos;
- Extração do mínimo reutilizável após o primeiro caso real validado.
