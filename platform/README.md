# Platform — núcleo modular da Content Factory

Esta pasta contém as fatias implementadas do núcleo modular previsto em
[`docs/decisoes/MKT-VIDEO-001-producao-modular.md`](../docs/decisoes/MKT-VIDEO-001-producao-modular.md),
[`docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md`](../docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md)
e [`docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md`](../docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md):

1. **Primeira fatia** — Manifesto de projeto → validação → relatório estruturado → testes com dois projetos diferentes.
2. **Segunda fatia** — Composition v1 → vínculo entre projeto e composição → validação → relatório estruturado → CLI → testes com dois projetos.
3. **Terceira fatia (R001)** — catálogo declarativo de perfis de saída sociais → regras oficiais com escopo por contexto e pendências de fonte → `OutputPlan` canônico → compatibilidade Composition × OutputPlan → CLIs `content:profiles` e `content:plan-output`.
4. **Fronteira pública mínima (`TEMPORAL-02-01`)** — Entrypoint público compilado (`dist/src/composition-validation-api.js` + `.d.ts`) para consumo externo de `validateComposition(composition, project)` sem importar `platform/src` nem caminhos internos de `dist/`.
5. **BeatPlan v1 (fatia interna)** — tradução **temporal** declarativa de uma Composition válida: beats ordenados com `startMs`/`durationMs`, função narrativa, texto e intenções → schema draft-07 → validador vinculado a ProjectManifest e Composition → CLI `content:validate-beat-plan` → dois exemplos versionados. Sem export público, sem `OutputPlan`, sem Temporal, sem render e sem mídia.
6. **Validação consolidada do pipeline** — `validateContentPipeline` unifica ProjectManifest → Composition → OutputPlan → compatibilidade Composition × OutputPlan → BeatPlan em uma execução pura e determinística, com CLI `content:validate-pipeline`.
7. **Casos de pipeline e segundo consumidor real (fatia interna)** — `ContentPipelineCaseManifest` amarra os quatro documentos por caminhos relativos, com resolvedor seguro confinado a uma raiz declarada, validação de um caso, agregação multiprojeto e CLI `content:validate-cases`. A Multitrack Hub entra como segundo consumidor real ao lado da Marca Salão, sobre o mesmo núcleo, sem condicional de marca. Sem export público, sem Temporal, sem render e sem mídia.
8. **CreativeExecutionPackage v1 (fatia interna)** — especificação técnica imutável da execução futura, gerada **somente depois de um pipeline válido**: contrato, schema draft-07, gerador puro, validador puro, serialização canônica, packageId determinístico, artefatos esperados lógicos, geração multicase e CLI transacional `content:build-execution-packages`. Nenhum renderizador, Worker ou adaptador é implementado; o pacote não executa nada.
9. **Executor local simulado v1 (fatia interna)** — consome o `CreativeExecutionPackage` e produz **somente** plano de execução, eventos determinísticos, relatório final, artefatos lógicos textuais simulados e manifesto de hashes: contratos `SimulatedExecutionPlan`/`SimulatedExecutionReport`, compilador puro, runner com falha/cancelamento controlados, retomada segura, writer transacional, multicase e CLI `content:simulate-execution`. O adaptador `simulation` é verificação de contrato — **não é renderer** e nenhuma mídia é produzida.

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
| `name` | Obrigatório, com ao menos um caractere não em branco (opaco ao núcleo) |
| `locale` | Obrigatório, com ao menos um caractere não em branco (opaco ao núcleo) |
| `timezone` | Obrigatório, com ao menos um caractere não em branco (opaco ao núcleo) |
| `brandTheme` | Obrigatório, com ao menos um caractere não em branco e **opaco ao núcleo** |
| `assetRoot` | Caminho **relativo seguro**: sem caractere de controle, sem absoluto (POSIX, unidade Windows, UNC), sem URL/protocolo, sem `..` e sem referências sensíveis por nome/extensão (ver *Segurança de caminhos*) |
| `contentPolicies` | Objeto com exatamente 4 booleanos explícitos (ausência é erro, não default) |
| `outputProfiles` | Array não vazio, itens em kebab-case, sem duplicatas |
| campos desconhecidos | **Proibidos** no topo e em `contentPolicies` (`additionalProperties: false`) |

## Códigos de validação (estáveis)

`PROJECT_MANIFEST_INVALID`, `PROJECT_SCHEMA_VERSION_UNSUPPORTED`, `PROJECT_ID_REQUIRED`,
`PROJECT_ID_INVALID`, `PROJECT_NAME_REQUIRED`, `PROJECT_LOCALE_REQUIRED`,
`PROJECT_TIMEZONE_REQUIRED`, `PROJECT_BRAND_THEME_REQUIRED`, `PROJECT_ASSET_ROOT_REQUIRED`,
`PROJECT_ASSET_ROOT_CONTROL_CHARACTER`, `PROJECT_ASSET_ROOT_ABSOLUTE`, `PROJECT_ASSET_ROOT_URL`,
`PROJECT_ASSET_ROOT_TRAVERSAL`, `PROJECT_ASSET_ROOT_SENSITIVE`,
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
| `title` | Obrigatório, com ao menos um caractere não em branco (opaco ao núcleo) |
| `locale` | Obrigatório, não em branco; na v1 deve ser **igual** a `project.locale` |
| `format` | Objeto com `profile` (kebab-case, presente em `project.outputProfiles`), `width` e `height` inteiros positivos e `fps` inteiro entre 1 e 120 |
| `scenes` | Array de cenas: `id` kebab-case único, `type` em `text`/`image`/`video`/`cta`, `durationMs` inteiro seguro (> 0 e <= `Number.MAX_SAFE_INTEGER`) e `content` em forma fechada por tipo |
| `renderer` | Objeto com `adapter` kebab-case obrigatório; `undecided` é aceito e nenhum adapter precisa estar instalado; `options` não é suportado na v1 |
| `metadata` | Opcional e pequeno: `status` em `draft`/`review`/`approved`/`archived`, `description` e `tags` (strings não em branco, sem duplicata, no máximo 8) |
| campos desconhecidos | **Proibidos** no topo, em `format`, em cada cena, em `content`, em `asset`, em `renderer` e em `metadata` |

`content` por tipo: `text` exige `text` e proíbe `asset`; `cta` exige `text` e aceita
`href` somente http(s) absoluto, com hostname e **sem username nem password** (a URL
nunca é acessada — é tratada como dado); `image` e `video` exigem `asset` e aceitam
`alt`. `alt`, `accessibilityLabel` e os demais campos textuais são opcionais onde o tipo
os permite, mas quando presentes exigem ao menos um caractere não em branco.

### Fonte normativa da estrutura

A estrutura dos contratos tem **três descrições**, e cada uma tem seu papel:

| Artefato | É a fonte normativa de | Não decide |
|---|---|---|
| `src/project-contract.ts` e `src/composition-contract.ts` (tipos) | a forma da estrutura: quais campos existem, quais tipos de cena há, qual `content` pertence a qual `type` | semântica entre documentos |
| `schemas/*.schema.json` (draft-07) | a forma **estrutural** verificável fora do TypeScript | regras que o vocabulário draft-07 não expressa |
| `src/validate-project.ts` e `src/validate-composition.ts` | **implementação de referência**: aceitação, códigos públicos, ordem de emissão e relatório | — |

`CompositionScene` é uma **união discriminada por `type`**
(`CompositionTextScene | CompositionImageScene | CompositionVideoScene | CompositionCtaScene`),
então o compilador rejeita combinações inválidas de `type`/`content` antes de qualquer
execução. A superfície de `content` por tipo existe em um único lugar —
`COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE` —, usada pelo validador para rejeitar campos,
espelhada nas chaves de `#/definitions/*Content.properties` no schema e conferida nos
testes de contrato contra as duas fontes. `CompositionSceneOfType<T>` (`Extract` por tipo)
é o narrowing público.

O teste de compilação é o próprio `tsc`: `tests/contracts/type-discrimination.test.ts`
marca cada combinação inválida com `@ts-expect-error`. Se o TypeScript deixar de rejeitar
uma delas, a diretiva fica não-usada, o build falha e o gate inteiro para. Não há `any`,
`@ts-ignore` nem relaxamento de `strict` nesse mecanismo — `npm run build` e
`npm run typecheck` **são** o teste de tipos.

## AssetReference mínimo

`asset` tem somente `id` (kebab-case) e `path` (caminho relativo seguro: sem caractere de
controle, sem absoluto, sem `..`, sem URL/protocolo e sem referências sensíveis por
nome/extensão — ver *Segurança de caminhos*). **AssetReference não substitui o futuro
AssetManifest**: hash, licença, origem, provider, prompt, dimensões e duração pertencem a
uma fatia futura.

## Metadata técnica ≠ autorização editorial

`metadata.status: "approved"` é um estado **técnico** do artefato declarativo. Ele não
concede autorização editorial, de gravação ou de publicação: essas autorizações
continuam regidas por `AGENTS.md`, `WORKFLOW.md` e pelos briefings aprovados.

A fronteira vale para todo o núcleo: **documento estruturalmente válido não é produto
aprovado**. Exit code `0` das CLIs, `valid: true` no relatório e um job verde no gate
significam apenas que o manifesto e a composição respeitam o contrato. Eles não dizem que
o conteúdo é verdadeiro, que a arte existe no disco, que há renderizador instalado, que o
briefing/roteiro foi aprovado pelo titular ou que algo pode ser publicado ou agendado.

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
`COMPOSITION_ASSET_PATH_REQUIRED`, `COMPOSITION_ASSET_PATH_CONTROL_CHARACTER`,
`COMPOSITION_ASSET_PATH_ABSOLUTE`, `COMPOSITION_ASSET_PATH_URL`,
`COMPOSITION_ASSET_PATH_TRAVERSAL`, `COMPOSITION_ASSET_PATH_SENSITIVE`,
`COMPOSITION_CTA_HREF_INVALID`,
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

## Catálogo de perfis de saída e OutputPlan (R001)

Terceira fatia executável da plataforma: **declarar** os formatos sociais que as ferramentas
desta caixa já exportam e **resolver** o plano canônico de um perfil para um projeto. Nada
aqui gera mídia, renderiza, publica ou acessa rede. A origem normativa de cada limite, as
pendências de fonte e as escolhas de desenho estão em
[`docs/planejamento/R001-formatos-sociais.md`](../docs/planejamento/R001-formatos-sociais.md).

| Peça | Onde | Papel |
|---|---|---|
| `CATALOG_VERSION` (`"1"`, 12 perfis) | `src/output-profiles/catalog.ts` | geometria, `fps` **só em vídeo**, `revision` declarada no perfil e capacidade de exportação observada (`preset-only` → `canvas-template-mapped` → `tool-export-observed`) com a evidência de cada estado |
| `CATALOG_RULES` | `src/output-profiles/rules.ts` | regras oficiais (`R-*`), defaults internos (`D-LOCAL-*`) e pendências de fonte (`P-*`); cada regra oficial declara **`contexts`** — a lista de contextos de publicação em que aquele texto vale |
| `resolveOutputPlan` | `src/resolve-output-profile.ts` | manifesto + perfil + filtros → `OutputPlan` canônico ou erro estável |
| `validateCompositionForOutputPlan` | `src/validate-composition-output.ts` | três camadas independentes: plano, composição, compatibilidade |
| `schemas/output-plan.schema.json` | draft-07 | espelho normativo do plano, executado por `ajv` nos testes |

Não existe tabela paralela de limites: o allowlist é lido do manifesto do projeto pelas
mesmas funções do resolvedor, `revision` pertence ao perfil, e um limite cujos `contexts`
não incluem o contexto declarado produz `OUTPUT_PLAN_RULE_NOT_APPLIED` em vez de uma
verificação silenciosa.

### Contrato de `content:profiles`

Flags: `--network instagram|facebook|youtube` · `--publication feed|stories|reels|shorts|video` ·
`--media image|video` · `--project <caminho>` · `--json`. Exit codes: `0` listagem produzida
(lista vazia é resultado válido) · `1` o JSON do projeto é legível mas o manifesto foi
rejeitado · `2` erro de uso, arquivo ausente ou JSON malformado.

**Sem `--project` a permissão de cada perfil é `not-consulted` — nunca "permitida".** Com
`--project`, a disponibilidade vem do allowlist do manifesto:

| `availability` | Quando | Campos auxiliares |
|---|---|---|
| `allowed` | o `id` está em `outputProfiles` do projeto | `blockCode` e `blockReason` são `null` |
| `blocked` | o `id` não está no allowlist (`OUTPUT_PROFILE_NOT_ALLOWED`) ou o manifesto foi rejeitado (`OUTPUT_PROJECT_INVALID`) | `blockCode` + `blockReason` explicam o bloqueio |
| `not-consulted` | nenhum projeto informado | `blockCode` e `blockReason` são `null` |

O documento `--json` tem exatamente estas chaves, em ordem estável:

```json
{
  "catalogVersion": "1",
  "filters": { "network": "youtube", "publication": null, "mediaKind": null },
  "project": { "consulted": true, "valid": true, "id": "marca-salao" },
  "counts": { "listed": 2, "allowed": 2, "blocked": 0, "notConsulted": 0 },
  "profiles": [
    {
      "id": "youtube-shorts", "name": "Shorts do YouTube", "revision": 3,
      "network": "youtube", "publication": "shorts", "mediaKind": "video",
      "width": 1080, "height": 1920, "aspectRatio": "9:16", "fps": 30,
      "exportState": "canvas-template-mapped",
      "exportEvidence": ["templates/story_reel_vertical/index.html:5"],
      "pendingRuleIds": ["P-YT-03"],
      "availability": "allowed", "blockCode": null, "blockReason": null
    }
  ],
  "diagnostics": [],
  "summary": "Catalogo v1: 2 perfil(es) listado(s); permissao consultada no allowlist do projeto \"marca-salao\" (2 habilitado(s), 0 bloqueado(s))."
}
```

`fps` é `null` em perfil de imagem. `diagnostics` traz os issues do validador de manifesto
quando `project.valid` é `false`; a listagem bloqueada continua sendo impressa antes do
diagnóstico, e o processo termina com exit `1`.

### Contrato de `content:plan-output`

Flags: `--project <caminho>` e `--profile <id>` **obrigatórios**; `--network`, `--publication`,
`--media` (restrição cruzada de seleção), `--rule-context in-app|api-publishing|ads|studio-upload`,
`--composition <caminho>` (verificação opcional) e `--json`. Exit codes: `0` plano resolvido e,
se a composição foi informada, compatível · `1` plano, seleção ou compatibilidade inválidos ·
`2` erro de uso, arquivo inexistente ou JSON malformado.

Em `--json` o stdout é **exatamente** `resolution.plan` (indentação de dois espaços, newline
final), então os bytes emitidos são re-leríveis pelo schema e por `validateOutputPlan` sem
nenhuma edição. A verificação de Composition acontece **antes** de emitir, para nunca imprimir
um plano cuja composição já se sabe que não casa. Todo o resto — avisos, códigos por camada,
`pendencias de fonte:` e `requer inspecao:` — sai em stderr **inclusive no sucesso**, porque
"o que ainda não pode ser certificado" não é erro. No modo humano (sem `--json`) o plano é
impresso no stdout junto dessas duas linhas, e os avisos continuam em stderr. Na falha o
stdout fica vazio nos dois modos.

Ordem canônica das chaves do plano: `schemaVersion, projectId, catalogVersion, profileId,
profileRevision, mediaKind` e, então, `ruleContext` (se declarado) mais `image` **ou** `video`
— nunca os dois, e `fps` só existe no ramo de vídeo.

## BeatPlan v1 (fatia interna)

O BeatPlan é a **tradução temporal** de uma Composition válida: uma sequência ordenada de
beats, cada um com início, duração, função narrativa, texto e intenções. Ele não é roteiro,
não é Composition e não é renderização — **não** gera beats automaticamente, não contém
comando de ferramenta, não contém provider de mídia e não cria arquivos. A fatia é
**interna ao pacote**: ver *Fronteira pública mínima* abaixo.

| Peça | Onde | Papel |
|---|---|---|
| Contrato TypeScript v1 | `src/beat-plan-contract.ts` | `BeatPlan`, `Beat`, enums neutros (função narrativa, `motionIntent`, transições, `validationStatus`) e os limites documentados de texto e tags; nenhuma chave de projeto, fornecedor ou prompt executável |
| Relatório aditivo | `src/validation-report.ts` (`BeatPlanValidationReport`) | mesma política dos relatórios existentes: ordem estável, sem timestamp, sem caminho absoluto, sem stack trace |
| Espelho draft-07 | `schemas/beat-plan.schema.json` | só a forma estrutural, executado por `ajv` em `tests/contracts/beat-plan-schema.test.ts` |
| Validador de referência | `src/validate-beat-plan.ts` — `validateBeatPlan(beatPlan, composition, project)` | confere manifesto, composição, estrutura, vínculo, cenas e timeline |
| CLI | `src/validate-beat-plan-cli.ts`, script `content:validate-beat-plan` | `--project` + `--composition` + `--beat-plan` [+ `--json`], montada sobre o mesmo `src/cli-input.ts` das CLIs de saída |
| Exemplos | `examples/beat-plans/*.beat-plan.json` | dois planos versionados, um por par oficial de Composition/ProjectManifest |

**Relação com os contratos existentes.** Os três documentos são sempre entrada explícita: o
núcleo não lê arquivos, não abre assets, não acessa rede e não conhece projeto específico, e
nenhuma entrada é mutada. A ordem de emissão é fixa — `project` → `composition` → estrutura
do plano → vínculo entre os três → relação com as cenas → timeline — e um manifesto ou uma
composição inválidos produzem `BEAT_PLAN_PROJECT_MANIFEST_INVALID` /
`BEAT_PLAN_COMPOSITION_INVALID`: o BeatPlan **delega** chamando `validateProjectManifest` e
`validateComposition`, em vez de reescrever as regras alheias.

**Timeline v1, estritamente linear.** O primeiro beat começa em `0`, os beats são contíguos
(sem lacuna nem sobreposição) e o último termina exatamente na duração total da Composition
(`BEAT_PLAN_TIMELINE_END_MISMATCH` fora disso). Nenhum tempo é corrigido, reordenado ou
preenchido automaticamente. Todo `sceneId` precisa existir na composição, mas cena e beat
**não** têm relação um para um: um beat pode atravessar duas cenas e uma cena pode aparecer em
mais de um beat. Cena não referenciada é aviso (`BEAT_PLAN_SCENE_UNREFERENCED`), não erro.

**Texto, não áudio.** `narration` é `{ text }` e nada mais: não há voz, provider, arquivo nem
configuração de TTS, porque `AudioPlan` é fatia futura. É assim que a política de produção
desta caixa — vídeo entregue sem áudio, narração entregue como texto separado — cabe no
contrato. `motionIntent` e as transições descrevem **intenção** e não executam movimento nem
animação.

**Estado técnico ≠ autorização editorial.** `validationStatus: "validated"` e
`metadata.status: "validated"` registram revisão técnica; nenhum estado concede aprovação
editorial, autorização de gravação, de produção ou de publicação. Os avisos de comprimento e
de tempo de leitura (`*_TEXT_LONG`, `BEAT_PLAN_READING_TIME_RISK`) são heurísticas técnicas e
não substituem a leitura humana cronometrada.

**O que o schema não decide.** Igualdade de `projectId`/`compositionId`/`locale`, existência
de `sceneId`, continuidade e duração total não são expressáveis no vocabulário draft-07 e
pertencem ao core — a mesma fronteira de *Regras do schema × regras do core*.

**Fronteiras desta fatia.** O BeatPlan não entra no entrypoint público
(`composition-validation-api.ts` continua exportando apenas `validateComposition`) e não ganha
subpath: `marcasalao-marketing-platform/dist/src/beat-plan-contract.js` responde
`ERR_PACKAGE_PATH_NOT_EXPORTED`. Não há integração com `OutputPlan` nem com o catálogo de
saída, nada em `orchestration/temporal/` foi tocado e nenhum import de `@temporalio/*` existe.
Não renderiza, não gera mídia, não abre asset e não publica. `VisualStyle`, `VisualAnchor`,
`AssetManifest`, `AudioPlan` e `RenderPlan` continuam fatias futuras.

## Fronteira pública mínima (`TEMPORAL-02-01`)

Para permitir consumo por outro pacote sem acoplamento à estrutura interna de `platform/src`
ou a caminhos relativos arbitrários de `dist/`, o pacote expõe um único entrypoint público:

- **Nome do pacote**: `marcasalao-marketing-platform` (`private: true`, uso local/empacotado, não publicado no npm)
- **Entrypoint-fonte**: `src/composition-validation-api.ts`
- **Artefatos compilados expostos em `package.json`** (`main`, `types` e `exports["."]`) e incluídos em `files` (`dist/src`, sem `*-cli.*`):
  - JavaScript ESM: `./dist/src/composition-validation-api.js`
  - Declarações TypeScript: `./dist/src/composition-validation-api.d.ts`
- **Superfície pública permitida**:
  - Runtime: exclusivamente `validateComposition`
  - Tipos (`export type`): `Composition`, `ProjectManifest` e `CompositionValidationReport`
- **Ordem obrigatória dos argumentos**: `validateComposition(composition, project)` — `Composition` primeiro, `ProjectManifest` depois. A ordem invertida não é equivalente e produz relatório inválido (`COMPOSITION_MANIFEST_INVALID`).
- **Proibição de imports internos**: consumidores externos devem importar apenas pelo nome público `marcasalao-marketing-platform`. Subpaths internos (`marcasalao-marketing-platform/dist/...` ou `marcasalao-marketing-platform/src/...`) são bloqueados pelo mapa `exports` do Node (`ERR_PACKAGE_PATH_NOT_EXPORTED`), e CLIs, helpers internos, `OutputPlan` ou `BeatPlan` não são exportados.
- **Independência de runtime**: `platform` permanece com zero dependências de runtime e sem qualquer dependência ou import de `@temporalio/*` ou `orchestration`. Activity e Workflow Temporal **não** fazem parte desta fatia.

```ts
import {
  validateComposition,
  type Composition,
  type CompositionValidationReport,
  type ProjectManifest,
} from 'marcasalao-marketing-platform'

const report: CompositionValidationReport = validateComposition(composition, project)
```

## Como executar

Requisito: **Node >= 22** (runtime mínimo, declarado em `engines`: `>=22 <25`). O
TypeScript é **compilado para JavaScript antes da execução** (`tsc` → `dist/`); nenhuma
execução direta de `.ts` é necessária. Zero dependências de runtime.

```bash
# a partir de platform/
npm ci                    # instala as devDependencies (typescript, @types/node, ajv)
npm run clean             # apaga dist/ (script Node portátil)
npm run build             # compila src/ e tests/ para dist/ (tsc, NodeNext)
npm run typecheck         # tsc --noEmit
npm test                  # build + node --test "dist/tests/**/*.test.js" (JavaScript compilado)
npm run test:contracts    # build + node --test "dist/tests/contracts/*.test.js" (só os contratos)

# CLI compilada (exit 0 válido · 1 manifesto inválido · 2 uso/JSON malformado)
npm run content:validate-project -- --project examples/projects/marca-salao.project.json --json
npm run content:validate-project -- --project examples/projects/fixture-project.project.json

# CLI de composicao (exit 0 válida · 1 inválida · 2 uso/JSON malformado)
npm run content:validate-composition -- --project examples/projects/marca-salao.project.json --composition examples/compositions/marca-salao-pilot.composition.json --json
npm run content:validate-composition -- --project examples/projects/fixture-project.project.json --composition examples/compositions/fixture-project-pilot.composition.json

# listagem do catalogo de saida (exit 0 · 1 manifesto rejeitado · 2 uso)
npm run --silent content:profiles -- --network youtube --media video
npm run --silent content:profiles -- --project examples/projects/marca-salao-social.project.json --json

# plano de saida canonico (exit 0 · 1 plano/selecao/compatibilidade invalidos · 2 uso)
npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json --profile instagram-reels-video --composition examples/compositions/marca-salao-social-reel.composition.json --json
npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json --profile youtube-shorts --rule-context studio-upload

# o mesmo stdout regravado sobre o fixture é byte a byte igual (tests/output-plan-examples.test.ts)
npm run --silent content:plan-output -- --project examples/projects/marca-salao-social.project.json --profile youtube-shorts --rule-context studio-upload --json > examples/output-plans/youtube-shorts-studio-upload.output-plan.json

# CLI de beat plan (exit 0 valido · 1 plano/projeto/composicao invalidos · 2 uso/JSON malformado)
npm run --silent content:validate-beat-plan -- --project examples/projects/marca-salao.project.json --composition examples/compositions/marca-salao-pilot.composition.json --beat-plan examples/beat-plans/marca-salao-pilot.beat-plan.json --json
npm run --silent content:validate-beat-plan -- --project examples/projects/fixture-project.project.json --composition examples/compositions/fixture-project-pilot.composition.json --beat-plan examples/beat-plans/fixture-project-pilot.beat-plan.json

# CLI de validacao consolidada do pipeline (exit 0 valido · 1 invalido · 2 uso/arquivo ausente/JSON malformado)
npm run --silent content:validate-pipeline -- --project examples/projects/marca-salao-social.project.json --composition examples/compositions/marca-salao-social-reel.composition.json --output-plan examples/output-plans/instagram-reels-video.output-plan.json --beat-plan examples/pipelines/marca-salao-social-reel.beat-plan.json --json

# CLI multiprojeto de casos (exit 0 valido(s) · 1 invalido(s) de dominio · 2 uso/ilegivel/descoberta vazia)
npm run --silent content:validate-cases -- --case examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json --root examples --json
npm run --silent content:validate-cases -- --cases-root examples --json

# CLI de geracao de pacotes de execucao (exit 0 gerados · 1 caso invalido · 2 uso/path/manifesto · 3 geracao/validacao do pacote · 4 escrita/promocao)
npm run --silent content:build-execution-packages -- --manifest <cases-manifest.json> --output-dir <diretorio> --json

# CLI do executor local simulado (exit 0 concluidas · 1 falha/cancelamento · 2 uso/path/JSON · 3 pacote/plano · 4 escrita/hash · 5 retomada incompativel)
npm run --silent content:simulate-execution -- --package examples/execution-packages/execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan.execution-package.json --output-dir <diretorio> --json
npm run --silent content:simulate-execution -- --packages-dir examples/execution-packages --output-dir <diretorio> --json
```

`dist/` é **artefato local** gerado pelo build e está ignorado pelo Git
(`platform/.gitignore`). Os exemplos JSON continuam sendo lidos da árvore-fonte
(`platform/examples/projects/`); o caminho informado em `--project` é resolvido em
relação ao diretório atual de execução.

Exit codes da CLI: `0` válido · `1` manifesto inválido (relatório emitido) · `2` erro de
uso, arquivo inexistente ou JSON malformado (mensagem sanitizada, sem stack trace).

### Exemplos que executam

| Arquivo | O que prova |
|---|---|
| `examples/projects/marca-salao.project.json` | manifesto oficial do consumidor (allowlist mínimo) |
| `examples/projects/marca-salao-social.project.json` | manifesto **técnico** de demonstração: reusa o `id` `marca-salao` e amplia o allowlist para imagem quadrada, Reels de cada rede, vídeo horizontal e Shorts |
| `examples/compositions/marca-salao-pilot.composition.json` | composição antiga do piloto, aceita sobre `vertical-social` — é ela que demonstra `OUTPUT_COMPAT_PROFILE_MISMATCH` |
| `examples/compositions/marca-salao-social-reel.composition.json` | composição positiva em `instagram-reels-video` (14 s, sem áudio) |
| `examples/output-plans/*.output-plan.json` | 5 planos canônicos gerados pelo stdout da CLI, comparados byte a byte e relidos por `ajv` + `validateOutputPlan` |
| `examples/beat-plans/marca-salao-pilot.beat-plan.json` | plano de 4 beats (10000 ms) sobre a composição do piloto: um beat atravessa `demo-frame` e `closing`, e o plano fecha exatamente com a composição — zero erro e zero aviso |
| `examples/beat-plans/fixture-project-pilot.beat-plan.json` | plano de 2 beats (5000 ms) em `en-US` sobre a composição do fixture: um beat sem `narration` é aceito, porque narração é opcional por design |
| `examples/projects/multitrack-hub-social.project.json` | manifesto técnico do segundo consumidor real (Multitrack Hub), com allowlist próprio e políticas explícitas |
| `examples/compositions/multitrack-hub-social-reel.composition.json` | composição positiva do segundo consumidor em `instagram-reels-video` (15 s, sem áudio, CTA para o site oficial documentado) |
| `examples/output-plans/multitrack-hub-instagram-reels-video.output-plan.json` | plano canônico do segundo consumidor, gerado pelo stdout de `content:plan-output` e comparado byte a byte |
| `examples/pipelines/multitrack-hub-pipeline-pilot.pipeline.json` | manifesto de caso que amarra os quatro documentos da Multitrack Hub; validado junto com o caso da Marca Salão pela CLI multiprojeto |
| `examples/execution-packages/*.execution-package.json` | pacotes técnicos canônicos dos dois consumidores, gerados pela CLI `content:build-execution-packages` e comparados byte a byte (gerador em memória, serialização, fixture e CLI); não são render nem job executado |
| `examples/simulated-executions/marca-salao/`, `examples/simulated-executions/multitrackhub/` | execuções simuladas canônicas (plano, relatório, eventos, hashes e artefatos textuais), produzidas pelo próprio executor e comparadas byte a byte; não são render nem mídia |

Nenhum desses arquivos autoriza publicação: são fixtures de contrato. A demonstração da
divergência exige que a composição antiga **primeiro** passe em `validateComposition` — há
teste que prova isso antes do teste de compatibilidade. Os dois beat plans recebem o mesmo
tratamento em `tests/beat-plan-examples.test.ts`: a referência é conferida no disco, o schema
e o core rodam sobre o arquivo, a CLI é executada com ele, e os bytes são lidos em binário
para garantir LF sem CR e exatamente uma newline final — a regra `examples/beat-plans/*.json
text eol=lf` em `platform/.gitattributes` é o que impede o checkout do `windows-latest` de
converter o exemplo que o gate do Ubuntu lê.

## Gate automático (GitHub Actions)

Arquivo: `.github/workflows/platform-validation.yml`.

| Aspecto | Configuração |
|---|---|
| Gatilhos | `pull_request` e `push` **filtrados** por `platform/**` e pelo próprio workflow; `workflow_dispatch` para execução manual |
| Matriz | `ubuntu-latest` + `windows-latest` × Node `22` + `24` — os quatro dentro de `engines: ">=22 <25"` (`fail-fast: false`, para que um ambiente não oculte o veredito dos outros) |
| Cache | `actions/setup-node@v4` com `cache: npm` e `cache-dependency-path: platform/package-lock.json` |
| Ordem | `npm ci` → `npm run clean` → `npm run typecheck` → `npm test` → prova do ramo de falha → upload dos logs, todas com `working-directory: platform` e `shell: bash` nos dois sistemas |
| Permissões | `contents: read`; nenhum segredo é referenciado no arquivo |
| Diagnóstico | cada passo de verificação passa por `scripts/gate-step.sh`, que grava a saída completa em `platform/gate-logs/`, escreve o resumo no `GITHUB_STEP_SUMMARY` e devolve o **exit code original do comando**, mesmo quando o comando falha; `actions/upload-artifact@v4` publica os logs **só em falha**, com nome por combinação da matriz |

`gate-step.sh` existe porque o runner chama cada passo com `bash --noprofile --norc -e -o
pipefail`. Sob esse `errexit`, o pipeline `npm test 2>&1 | tee …` que falha **encerra o passo
na hora**: a linha seguinte (`code=$?`) e o resumo nunca eram executados, e o diagnóstico
ficava reduzido ao TAP do artifact. O script suspende o `errexit` só durante o pipeline, lê
`PIPESTATUS` em uma única atribuição (o primeiro `var=${PIPESTATUS[0]}` já reinicia o array) e
decide o código final assim: se o comando falhou, devolve o código dele; se só o `tee` falhou,
devolve o do `tee` — uma falha de gravação de log nunca vira sucesso silencioso. Como o
Windows converte texto para CRLF no checkout, `platform/.gitattributes` fixa `*.sh text eol=lf`
para o script continuar executável nos quatro ambientes e também
`examples/output-plans/*.json text eol=lf` para os planos canônicos de OutputPlan: esses
exemplos usam LF, a regra evita divergência CRLF/LF no checkout Windows e a comparação entre
o stdout da CLI e o fixture versionado permanece byte a byte (`tests/output-plan-examples.test.ts`).
A mesma razão vale para `examples/beat-plans/*.json text eol=lf`, acrescentado com o BeatPlan:
os dois planos versionados são lidos em binário por `tests/beat-plan-examples.test.ts`, que
exige LF, zero CR e uma única newline final — sem a regra, o `windows-latest` da matriz
checkoutaria CRLF e os quatro ambientes deixariam de ler os mesmos bytes.

A prova do ramo negativo é um passo do próprio workflow (`if: always()`), e não um ensaio
solto: ele roda o **mesmo** `gate-step.sh` com um comando que imprime duas linhas e termina
em `7`, exige `7` no código devolvido, exige as duas linhas no log e a linha de resumo
`ensaio-falha: codigo de saida 7 (tee 0)` no stdout do passo e no `GITHUB_STEP_SUMMARY`; em
seguida chama `gate-step.sh` com um destino de log inválido (o próprio diretório `gate-logs`)
e exige código **não zero**, provando que a falha do `tee` não é engolida. O `7` fica retido
numa variável do passo, então o ensaio só deixa o job vermelho se a captura quebrar.

`npm test` compila e roda a suíte inteira, **inclusive o corpus de contratos**
(`tests/contracts/*.test.js`) sobre o JavaScript de `dist/`; por isso o job não repete
`npm run test:contracts`, que existe para execução local focada. O `typecheck` é também o
teste de tipo: uma diretiva `@ts-expect-error` que deixa de falhar quebra o build.

`npm test` e `npm run test:contracts` fixam `--test-reporter=tap` **antes** dos padrões de
arquivo, então o log é o TAP completo — nomes dos testes, mensagens de asserção e o resumo
`# tests`/`# pass`/`# fail` — nos quatro ambientes da matriz. Isso é intencional: fora de TTY
o Node 22 já emite TAP por default, mas o Node 24 emite o repórter `spec`; depender do
default trocaria o formato do diagnóstico no meio da matriz. Uma opção colocada depois do
primeiro argumento posicional é ignorada pelo `node --test`, e há asserção em
`tests/build-portability.test.ts` que trava a ordem. O upload do artifact roda com
`if: failure()`, depois de o passo já ter marcado o job como vermelho: ele **acrescenta** o
log, não substitui o veredito, e não há retry automático em nenhum passo. Localmente o mesmo
padrão é o mesmo script: `bash scripts/gate-step.sh gate-logs/npm-test.tap "npm test" npm test`
(se o shell local não usa `errexit`, o passo se comporta igual); `gate-logs/` está no
`.gitignore` da `platform/`.

O gate cobre só o núcleo. `.github/workflows/video-preview.yml` segue com seus gatilhos e
passos originais (`02-reels-shorts/*.mp4` e `release`), sem alteração. E o limite continua
o mesmo do item anterior: **verde no gate = contrato estruturalmente válido**, não
renderização, não conteúdo verificado, não autorização de produção.

## Como adicionar um novo projeto

1. Copie um exemplo para um novo `*.project.json`;
2. Troque `id`, `name`, `locale`, `timezone`, `brandTheme`, `assetRoot`, políticas e
   `outputProfiles` para os valores do novo projeto;
3. Valide com a CLI (exit 0 esperado);
4. Nenhuma mudança no núcleo é necessária — se for, o contrato está sendo violado.

## Segurança de caminhos

A classificação léxica é **uma função pura compartilhada** (`src/relative-path.ts`,
`inspectRelativePath`) usada pelos dois contratos. Ela recebe a string e devolve as
violações em ordem fixa — `CONTROL_CHARACTER`, `ABSOLUTE`, `URL`, `TRAVERSAL`,
`SENSITIVE` — sem rede, sem leitura de assets, sem verificação de existência e sem
alterar a entrada. Cada contrato traduz a violação para os **próprios** códigos e caminhos
de erro: `PROJECT_ASSET_ROOT_*` para `assetRoot` e `COMPOSITION_ASSET_PATH_*` para
`asset.path`.

Rejeitam, nos dois contratos:

- caractere de controle (`U+0000`–`U+001F` e `U+007F`) em qualquer posição;
- caminho absoluto POSIX (`/var/assets`), com barras invertidas ou UNC
  (`\\servidor\share\a.png`) e letra de unidade Windows (`C:\assets\x`);
- URL ou qualquer protocolo (`http:`, `https:`, `file:` e protocol-relative `//…`);
- segmento `..` em qualquer um dos dois separadores;
- referências sensíveis **por segmento, nome e extensão**, nunca por substring do caminho
  inteiro: nomes pontados `.env`/`.env.local`/`.git` (e o que vier depois do ponto),
  extensões `.pem`, `.key`, `.p12`, `.pfx`, prefixos de chave SSH (`id_rsa`, `id_ecdsa`,
  `id_ed25519`) e nomes de segmento que sejam exatamente um de `secret(s)`, `password(s)`,
  `credential(s)`, `privatekey`, `serviceaccount` — comparados também com os tokens do nome
  (separados por `.`, `_`, `-`) e com o nome sem separadores.

Aceitam explicitamente (eram falsos positivos do antigo bloqueio por substring):
`assets/secretaria`, `assets/secretaria.png`, `assets/cenas/01.png`, `assets/keys/x.png`,
`assets/.gitignore`, `assets/env/.gitmodules`, `assets/passphrase.txt`.

A CLI lê **somente** o arquivo informado, não acessa rede, não altera arquivos, não cria
outputs e não lê `.env`. A **existência física** de assets não é verificada nesta fatia.

### Endurecimentos desta correção (documentados porque mudam entradas antes aceitas)

| Entrada | Antes | Agora |
|---|---|---|
| `assetRoot: "https://example.com/assets"` | aceita pelos dois motores | `PROJECT_ASSET_ROOT_URL` (schema: inválido) |
| caminho com caractere de controle (`assets` + NUL + `b.png`) | aceita pelos dois motores | `PROJECT_ASSET_ROOT_CONTROL_CHARACTER` / `COMPOSITION_ASSET_PATH_CONTROL_CHARACTER` |
| `href: "https://usuario@example.com"` (usuário sem senha) | aceita pelos dois motores | `COMPOSITION_CTA_HREF_CREDENTIALS` (schema: inválido) |
| string obrigatória só com espaços (`title`, `text`, `name`, `assetRoot`…) | aceita pelo schema | rejeitada pelos dois (`*_REQUIRED` / `pattern: \S`) |
| `durationMs` acima de `Number.MAX_SAFE_INTEGER` | rejeitada só pelo core | rejeitada também pelo schema (`maximum`) |
| protocolo do `href` em maiúsculas (`HTTPS://example.com`) | rejeitado só pelo schema | aceito pelos dois |
| `assets/secretaria`, `assets/secretaria.png` | rejeitados pelo core (substring) | aceitos pelos dois |
| `href: "http:/example.com"` e `href: "https:\\example.com"` (sem `://` literal) | **aceitos pelo core** porque `new URL()` normaliza; inválidos pelo schema | `COMPOSITION_CTA_HREF_INVALID` nos dois motores |
| `href: "https:///example.com"` e `"https:////example.com"` (autoridade vazia) | **aceitos pelo core** porque o parser descarta as barras extras e reconstrói o host; inválidos pelo schema | `COMPOSITION_CTA_HREF_INVALID` nos dois motores e saída `1` na CLI |
| `href: "https://\example.com"` (barra invertida no início da autoridade) | **aceitos pelos dois motores**: o parser descartava a barra, e a classe do schema não excluía a barra invertida | `COMPOSITION_CTA_HREF_INVALID` nos dois motores e saída `1` na CLI |
| `href: "https://example.com\@mencao"` (`@` em caminho aberto por barra invertida) | rejeitado pelos dois como credencial, embora o `@` esteja no caminho | aceito pelos dois motores e pela CLI |
| `href: "https://example.com?email=a@b.com"` e `"https://example.com#@contato"` (`@` em query/fragmento, sem barra depois do host) | aceitos pelo core, **rejeitados pelo schema** como se fossem credencial | aceitos pelos dois motores e pela CLI |

Os códigos anteriores (`*_ABSOLUTE`, `*_TRAVERSAL`, `*_SENSITIVE`, `COMPOSITION_ASSET_PATH_URL`,
`COMPOSITION_CTA_HREF_*`) e suas mensagens permanecem os mesmos; `*_URL` no manifesto e
`*_CONTROL_CHARACTER` nos dois contratos são os únicos códigos novos desta etapa.

## Regras do schema × regras do core

Os schemas draft-07 espelham a parte **estrutural** das regras; o validador TypeScript é a
implementação de referência e mantém as verificações **semânticas** que o vocabulário
draft-07 não expressa. Não há promessa de equivalência total, e cada divergência conhecida
é testada como diferença (nunca como equivalência) em `tests/path-url-validation.test.ts` e
no corpus classificado de `tests/contracts/`:

| Só o core (TypeScript) | Por quê |
|---|---|
| nomes sensíveis por **token** (`assets/secret.txt`, `assets/api-secrets.yaml`, `assets/service_account.json`) | exige segmentar o nome, normalizar separadores e comparar listas — não há predicado equivalente em draft-07 sem uma regex ilegível |
| host do `href` pelo **parser de URL** (`https://:8443`, `https://exa mple.com`) | o schema exige `scheme://` + primeiro caractere do host; a sintaxe completa é do `new URL()` |

**Nenhuma regra é só do schema.** A forma canônica `scheme://host` do `href` já era exigida
pelo espelho normativo e o core a aceitava por outra via, porque `new URL()` normaliza a
entrada antes de qualquer checagem. O validador agora inspeciona a string **original**, e o
espelho delimita a autoridade do mesmo jeito, nos dois lados do `scheme://`:

- **início da autoridade** (etapa 5 + etapa 6): `http:/exemplo.com` e `https:\\exemplo.com`
  não têm o prefixo literal; `https:///exemplo.com`, `https:////exemplo.com` e
  `https://\exemplo.com` têm autoridade vazia — o parser descarta as barras extras e
  reconstrói o host a partir do trecho seguinte, e por isso o core os aceitava (no caso da
  barra invertida, o próprio espelho também aceitava, porque a classe não excluía a barra).
  `https://?query` e `https://#fragmento` já falhavam nos dois e entram no corpus para
  manter a forma coberta. Todos viram `COMPOSITION_CTA_HREF_INVALID` **nos dois motores**,
  com saída `1` na CLI;
- **fim da autoridade** (etapa 6): a regex de credencial do espelho parava só em `/`, então
  um `@` de query ou fragmento (`https://exemplo.com?email=a@b.com`,
  `https://exemplo.com#@contato`) era lido como credencial e rejeitado **só pelo schema**.
  A autoridade agora termina em `/`, `?`, `#` ou barra invertida (separador de caminho para
  esquemas especiais, no parser do Node), então `@` em caminho, query ou fragmento é aceito
  pelos dois motores e pela CLI, com ou sem barra depois do host.

A rejeição de credenciais reais continua nos dois: `https://usuario@example.com`,
`https://user:pass@example.com`, `HTTPS://usuario:senha@example.com` e
`https://@example.com` seguem com `COMPOSITION_CTA_HREF_INVALID`/`..._CREDENTIALS`
preservados. Não sobrou divergência em que o schema declara inválida uma estrutura que o
core aceita como `valid: true` — nem o contrário em forma de estrutura válida rejeitada pelo
espelho.

O que **ambos** expressam e concordam caso a caso: absoluto (POSIX/unidade/UNC),
protocol-relative e protocolos, `..`, `.env*`/`.git*`, extensões de chave,
`id_rsa`/`id_ecdsa`/`id_ed25519`, caracteres de controle, strings obrigatórias não em
branco (`pattern: "\S"`), `durationMs <= 9007199254740991` e `href` com username ou senha
(inclusive protocolo em maiúsculas). Nenhuma extensão proprietária de schema é usada — só
o vocabulário draft-07.

## Corpus compartilhado e classificação dos casos

Um único corpus (`tests/contract-corpus.ts`), montado com os builders do harness
compartilhado (`tests/contract-harness.ts`: motor ajv real + builders de documentos +
leitura dos exemplos oficiais), roda **os mesmos objetos** contra o schema draft-07 e contra
o validador TypeScript. Não há tabelas duplicadas por arquivo. O BeatPlan fica fora desse
corpus: o harness só compila os schemas que já existiam e não exporta o motor, então
`tests/contracts/beat-plan-schema.test.ts` traz o próprio compile e o próprio corpus.

| Grupo | O que prova | Quem decide |
|---|---|---|
| `structuralProjectCases` (47) e `structuralCompositionCases` (134) | a regra vive na forma do próprio documento | **os dois precisam coincidir** no veredicto |
| `semanticCases` (21) | vínculo com o ProjectManifest (`projectId`, `locale`, `format.profile`), manifesto inválido, unicidade de `id` de cena, soma de `durationMs` com overflow, nomes sensíveis por token, sintaxe de `href` pelo parser e as heurísticas de warning | **só o TypeScript**; o veredicto do schema para o mesmo documento fica registrado em `schemaAccepts` |

Cada caso carrega nome, documento e (quando inválido) os **códigos exatos** esperados do
validador; os casos semânticos trazem também o projeto contra o qual são validados, o
motivo (`reason`) e os warnings esperados. O motivo da classificação é parte do corpus,
não um comentário solto: os testes de contrato exigem que todo `SemanticReason` documentado
tenha ao menos um caso.

Rodam em `tests/contracts/`:

- `structural-parity.test.ts` — os 181 casos estruturais, veredicto dos dois motores e
  códigos exatos do core, mais os dois pares oficiais;
- `semantic-rules.test.ts` — os 21 casos semânticos (códigos, warnings separados de erros,
  `totalDurationMs`, veredicto registrado do schema, imutabilidade da entrada e
  determinismo), incluindo a prova de que **o schema é mudo quanto ao vínculo**: a mesma
  composição é aceita pelo schema contra dois manifestos opostos enquanto o core produz
  `COMPOSITION_PROJECT_ID_MISMATCH`, `COMPOSITION_LOCALE_MISMATCH` e
  `COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED`;
- `type-discrimination.test.ts` — as combinações `type`/`content` rejeitadas em compilação
  (`@ts-expect-error`), paridade entre os tipos, `COMPOSITION_CONTENT_FIELDS_BY_SCENE_TYPE`
  e as propriedades do schema;
- `cli-parity.test.ts` — exit codes `0`/`1`/`2` das duas CLIs sobre amostras do corpus, com
  o JSON do processo igual ao relatório em memória, saída byte a byte idêntica entre
  execuções, ausência de caminho absoluto/timestamp/stack trace, arquivos intactos e, no
  limite da autoridade do `href`, os mesmos vereditos dos dois motores (os seis hrefs com
  `@` fora da autoridade saem `0`; os seis de autoridade vazia saem `1` com
  `COMPOSITION_CTA_HREF_INVALID`).
- `beat-plan-schema.test.ts` — o espelho draft-07 do BeatPlan sobre os objetos do próprio
  contrato, com as duas fronteiras registradas separadamente: o que a **forma** decide
  (aqui) e o que só o core decide (vínculo de ids, `locale`, existência de cena,
  continuidade e duração total). Os casos da segunda lista afirmam apenas o que o **motor**
  aceita, para que a ausência de regra fique registrada e ninguém confunda "o motor não
  reclamou" com equivalência.

`npm test` executa tudo (807 testes com o executor local simulado v1); `npm run
test:contracts` executa especificamente a verificação de contrato (305 testes) — ambas
sobre o JavaScript compilado em `dist/`.

## Regras textuais e de URL

`isNonEmptyString` (trim) vale para todo campo de texto obrigatório ou opcional: `name`,
`locale`, `timezone`, `brandTheme`, `assetRoot`, `title`, `locale` da composição, `text`,
`alt`, `accessibilityLabel`, `description`, `tags` e `asset.path`. "Apenas espaços" é erro,
não conteúdo.

`content.href` é validado **como dado**, na string original e depois com `new URL()`: o
prefixo `http(s)://` precisa estar literalmente na string, a autoridade entre `://` e o
primeiro `/`, `?`, `#` ou barra invertida não pode ser vazia nem começar em `@`, o protocolo
precisa ser `http:` ou `https:` (o parser normaliza a caixa) e o hostname precisa existir.
`username`/`password` preenchidos são rejeitados, e um `@` dentro dessa autoridade também é
credencial mesmo sem usuário escrito (`https://@example.com`); um `@` depois do fim da
autoridade é caminho, query ou fragmento e **não** é credencial. Nenhuma requisição, DNS ou
resolução de caminho é feita — nunca.

## Stack e dependências

- TypeScript com sintaxe erasable (sem enums/namespaces), **compilado com `tsc` antes
  da execução** (ESM/NodeNext, target ES2022, saída em `dist/`) — **zero dependências
  de runtime**;
- Validações explícitas escritas à mão (superfície pequena e enumerada); os arquivos
  `schemas/project.schema.json`, `schemas/composition.schema.json`,
  `schemas/output-plan.schema.json` e `schemas/beat-plan.schema.json` (JSON Schema
  draft-07) são a descrição normativa dos contratos e espelham os validadores. A cena é
  discriminada **inteira** pelo seu `type` no schema de composição (`oneOf` de quatro
  definições com `type` constante), porque a mesma forma de `content` pode pertencer a
  mais de um tipo;
- `node:test` nativo para os testes, executados sobre o JavaScript compilado em
  `dist/tests`;
- O espelho normativo é **executado** por um motor JSON Schema draft-07 real (`ajv`) no
  harness compartilhado `tests/contract-harness.ts`, usado por
  `tests/contracts/structural-parity.test.ts`, `tests/contracts/semantic-rules.test.ts`,
  `tests/composition-schema.test.ts` e `tests/path-url-validation.test.ts`, que comparam
  schema e validador TypeScript caso a caso, inclusive nos dois exemplos oficiais e nas
  divergências conhecidas entre os dois; o espelho do BeatPlan é executado pelo mesmo motor
  em `tests/contracts/beat-plan-schema.test.ts`, que traz o próprio `compile` porque o
  harness só conhece os schemas que já existiam;
- Os testes de **tipo** são o próprio `tsc`: as diretivas `@ts-expect-error` de
  `tests/contracts/type-discrimination.test.ts` falham o build se alguma combinação inválida
  de `type`/`content` deixar de ser rejeitada;
- DevDependencies apenas para o gate de tipos, o build e a execução dos schemas, fixadas:
  `typescript@5.9.3` (Apache-2.0), `@types/node@24.19.2` (MIT) e `ajv@8.20.0` (MIT).
  `ajv` é **dev-only**: nem o núcleo nem as CLIs o importam, e `dependencies` continua
  inexistente. Nenhum pacote de vídeo ou parser YAML foi adicionado;
- O gate de CI (`platform-validation.yml`) usa **exatamente essas devDependencies** —
  `npm ci` não instala runtime algum, porque não há o que instalar — e os quatro ambientes
  da matriz executam os mesmos scripts deste `package.json`, sem passo específico de CI.

## Validação consolidada do pipeline

A validação consolidada do pipeline criativo (`validateContentPipeline` em
`platform/src/validate-content-pipeline.ts`) unifica em uma única execução pura e
determinística a validação combinada de todos os contratos existentes:

1. **`project`** (`validateProjectManifest`) — integridade estrutural e políticas;
2. **`composition`** (`validateComposition`) — formato, cenas e vínculo com o projeto;
3. **`output-plan`** (`validateOutputPlan`) — preset, regras e catálogo de saída;
4. **`output-compatibility`** (`validateCompositionForOutputPlan`) — compatibilidade entre Composition e OutputPlan;
5. **`beat-plan`** (`validateBeatPlan`) — beats, timeline e função narrativa vinculados à Composition e ao projeto.

### Matriz de bloqueio (DAG de dependências)

Os validadores são chamados apenas quando suas pré-condições são satisfeitas, evitando diagnósticos ruidosos ou chamadas com dados incompatíveis:

- **Project inválido**: `project: invalid`; estágios dependentes (`composition`, `output-plan`, `output-compatibility`, `beat-plan`) ficam com `status: "blocked"` e `blockedBy: "project"`.
- **Composition inválida (com Project válido)**: `composition: invalid`; `output-plan` é avaliado de forma independente (depende apenas do Project); `output-compatibility` e `beat-plan` ficam `blocked` com `blockedBy: "composition"`.
- **OutputPlan inválido**: `output-plan: invalid`; `output-compatibility` fica `blocked` com `blockedBy: "output-plan"`; `beat-plan` é executado normalmente (depende apenas de Project e Composition válidos).
- **Compatibilidade inválida**: `output-compatibility: invalid`; `beat-plan` é executado normalmente; relatório consolidado é `invalid`.
- **BeatPlan inválido**: estágios anteriores permanecem preservados; `beat-plan: invalid`.

### Validade global e agregação

- `report.valid = true` se, e somente se, todos os estágios tiverem `status: "valid"` e `errors.length === 0`.
- **Warnings não invalidam o pipeline**: avisos legítimos (como cenas não referenciadas no BeatPlan) são preservados sem rebaixamento para erro nem descarte.
- Erros e warnings preservam código original, caminho lógico (`path`) e mensagem, prefixados pelo estágio de origem e ordenados deterministiscamente.
- O relatório consolidado (`ContentPipelineValidationReport`) preserva os relatórios originais de cada estágio em `stages` e ecoa `projectId`, `compositionId`, `outputPlanId` e `beatPlanId`.

### Exemplo resumido de relatório

```json
{
  "schemaVersion": 1,
  "valid": true,
  "summary": "Content pipeline is valid.",
  "projectId": "marca-salao",
  "compositionId": "social-reel-example",
  "outputPlanId": "instagram-reels-video",
  "beatPlanId": "social-reel-beat-plan",
  "stages": [
    { "stage": "project", "status": "valid", "report": { ... }, "blockedBy": null },
    { "stage": "composition", "status": "valid", "report": { ... }, "blockedBy": null },
    { "stage": "output-plan", "status": "valid", "report": { ... }, "blockedBy": null },
    { "stage": "output-compatibility", "status": "valid", "report": { ... }, "blockedBy": null },
    { "stage": "beat-plan", "status": "valid", "report": { ... }, "blockedBy": null }
  ],
  "errors": [],
  "warnings": [],
  "completedStages": ["project", "composition", "output-plan", "output-compatibility", "beat-plan"],
  "blockedStages": []
}
```

### CLI `content:validate-pipeline`

A CLI consome as flags `--project`, `--composition`, `--output-plan` e `--beat-plan`, com suporte opcional a `--json`:

- `0` — pipeline completo válido (`valid: true`);
- `1` — pipeline inválido de domínio (relatório estruturado emitido em stdout);
- `2` — erro de uso, flag inválida, arquivo ausente ou JSON malformado (stderr com stdout vazio).

## Casos de pipeline e CLI multiprojeto (segundo consumidor)

A validação consolidada recebe os quatro documentos em memória; o **caso de pipeline**
é a fatia que amarra esses documentos em disco, por manifesto, e prova que o mesmo
núcleo serve a mais de um consumidor real. Nesta fatia a **Multitrack Hub** entra como
segundo consumidor, ao lado da Marca Salão, sem nenhuma condicional de marca no núcleo.

| Peça | Onde | Papel |
|---|---|---|
| Contrato de caso | `src/content-pipeline-case-contract.ts` | `ContentPipelineCaseManifest` (`schemaVersion`, `id`, `project`, `composition`, `outputPlan`, `beatPlan`), validação estrutural pura e códigos estáveis `CASE_*` |
| Resolvedor seguro | `src/resolve-content-pipeline-case.ts` | lê o manifesto, resolve cada caminho relativo ao diretório do manifesto e exige confinamento estrito na raiz declarada, inclusive após resolver symlinks |
| Validação de um caso | `src/validate-content-pipeline-case.ts` | `validateContentPipelineCase` (puro) e `aggregateContentPipelineCases` (multiprojeto, ids únicos, ordem preservada) |
| Carga em disco | `src/content-pipeline-case-loader.ts` | descoberta determinística de `*.pipeline.json` (symlinks ignorados) e leitura dos quatro documentos via `cli-input.ts` |
| CLI interna | `src/content-pipeline-cases-cli.ts`, script `content:validate-cases` | modos `--case` e `--cases-root`, sobre o mesmo helper das demais CLIs |
| Fixtures do segundo consumidor | `examples/projects/multitrack-hub-social.project.json`, `examples/compositions/multitrack-hub-social-reel.composition.json`, `examples/output-plans/multitrack-hub-instagram-reels-video.output-plan.json`, `examples/pipelines/multitrack-hub-*` | caso técnico fictício coerente com a identidade documentada da Multitrack Hub; não é campanha aprovada |

**Modelo de segurança dos caminhos.** O contrato rejeita caminho absoluto, URL,
caractere de controle e referência sensível (mesma função lexical compartilhada
`relative-path.ts`). O segmento `..` é permitido no contrato porque os manifestos
referenciam diretórios irmãos (`../projects/…`); quem decide é o **confinamento**:
cada documento precisa resolver estritamente dentro da raiz declarada, e um symlink
que aponta para fora é rejeitado (`CASE_RESOLUTION_ESCAPE`). Documento ausente é
`CASE_DOCUMENT_MISSING`; manifesto ausente/malformado é
`CASE_MANIFEST_UNREADABLE`/`CASE_MANIFEST_MALFORMED`. Mensagens nunca ecoam caminho
absoluto da máquina.

**Estados do caso.** `valid` (manifesto e pipeline válidos), `invalid` (manifesto
válido, pipeline inválido — relatório consolidado preservado por inteiro),
`manifest-invalid` (estrutura do manifesto rejeitada) e `unreadable` (falha de
leitura, reportada pela camada de I/O). A agregação multiprojeto preserva a ordem
dos casos, rejeita ids duplicados (`CASE_DUPLICATE_ID`) e nunca considera válida
uma lista vazia (`CASES_EMPTY`).

**Contrato da CLI `content:validate-cases`.** Flags: `--case <manifesto>` com
`--root <raiz>` opcional (sem `--root`, a raiz de confinamento é o próprio diretório
do manifesto) **ou** `--cases-root <diretorio>` (descobre todos os `*.pipeline.json`
sob a raiz, em ordem determinística, e usa essa raiz como confinamento de todos os
casos); `--json` opcional. Exit codes: `0` caso(s) válido(s) · `1` caso(s) inválido(s)
de domínio ou manifesto estruturalmente inválido (relatório em stdout) · `2` erro de
uso, caso ilegível ou descoberta vazia (stderr com stdout vazio). O modo
`--cases-root examples` valida os dois consumidores reais em uma única execução.

**Comparação estrutural dos dois consumidores.** O teste de integração
`tests/content-pipeline-multiconsumer-examples.test.ts` executa os dois casos pelo
mesmo agregador e compara os relatórios: mesmos estágios na mesma ordem, mesmos
status, mesmos códigos de warning (`COMPOSITION_RENDERER_UNDECIDED`,
`OUTPUT_PLAN_CONTEXT_NOT_DECLARED`), zero erros; `projectId`, `compositionId` e
`beatPlanId` distintos; o OutputPlan da Multitrack Hub é byte a byte igual ao stdout
do resolvedor `content:plan-output`. As fixtures novas são técnicas e fictícias:
não reutilizam campanha publicada, não carregam credenciais, ids externos privados
nem dados pessoais, e não concedem autorização editorial.

**Fronteiras desta fatia.** O contrato de caso, o resolvedor, a agregação e a CLI
são **internos**: não entram no entrypoint público (`composition-validation-api.ts`
continua exportando apenas `validateComposition`), não ganham subpath em `exports`
e a CLI fica fora do tarball por `!dist/src/*-cli.*`. Nada em `orchestration/temporal/`
foi tocado; nenhum import de `@temporalio/*` existe; nenhuma renderização, mídia,
áudio, publicação ou deploy. O inventário fechado de `src/` e `schemas/` e a varredura
de independência de marca em `tests/beat-plan-validation.test.ts` foram estendidos
para cobrir os arquivos novos e proibir também referências à Multitrack Hub no núcleo.

## CreativeExecutionPackage v1 (pacote técnico de execução)

**Finalidade.** A validação consolidada responde "os documentos são válidos e
compatíveis?"; o `CreativeExecutionPackage` responde "qual é o pacote determinístico
que um executor futuro deverá consumir?". Ele é gerado **somente depois de um
`ContentPipelineValidationReport` válido** e é uma especificação técnica imutável da
execução futura: etapas, cenas, beats, perfil de saída e artefatos esperados.
**Validação não é execução**: nenhum renderizador, Worker ou adaptador existe nesta
fatia, e o pacote não executa nada — não renderiza, não gera vídeo/imagem/áudio, não
cria arquivos físicos de mídia, não acessa rede, não usa fornecedor, não entra no
Temporal e não publica.

| Peça | Onde | Papel |
|---|---|---|
| Contrato TypeScript v1 | `src/creative-execution-package-contract.ts` | `CreativeExecutionPackage`, `CreativeExecutionOutput`, `CreativeExecutionStep`, `ExpectedArtifact`, `CreativeExecutionSourceReferences`, códigos de falha e derivação do `packageId` |
| Espelho draft-07 | `schemas/creative-execution-package.schema.json` | forma estrutural, `additionalProperties: false`, executado por `ajv` nos testes |
| Gerador puro | `src/create-creative-execution-package.ts` — `createCreativeExecutionPackage(input, report)` | resultado discriminado `ok: true/package` ou `ok: false/failureCode`; só gera com pipeline válido; não revalida regras duplicadas; não muta entradas |
| Validador puro | `src/validate-creative-execution-package.ts` — `validateCreativeExecutionPackage(pkg)` | estrutura, IDs, output, timeline (ordem, `startMs`, `endMs`, contiguidade), duração consolidada, artefatos, unicidade, source references, propriedades extras |
| Serialização canônica | `src/serialize-creative-execution-package.ts` — `serializeCreativeExecutionPackage(pkg)` | ordem de campos explícita, indentação de 2 espaços, LF, uma newline final, UTF-8 sem BOM, round trip estável |
| Aplicação por caso e multicase | `src/creative-execution-packages.ts` | carrega o caso pelo loader, executa o pipeline, cria e valida o pacote; `createCreativeExecutionPackagesFromCases` com falha isolada e ordem estável |
| CLI interna | `src/creative-execution-package-cli.ts`, script `content:build-execution-packages` | manifesto de casos + output-dir confinado + geração transacional |
| Fixtures canônicas | `examples/execution-packages/*.execution-package.json` | um pacote por consumidor real, gerados pela própria CLI, comparados byte a byte |

**Contrato.** `schemaVersion: 1`; `packageId`; os quatro identificadores
(`projectId`, `compositionId`, `outputPlanId`, `beatPlanId`); `output`; `timeline`;
`expectedArtifacts`; `source`. Campos desconhecidos são proibidos em todos os níveis.

**Output.** Consolida somente dados já validados: `profileId`, `mediaKind` (`video`
na v1 — a compatibilidade Composition × OutputPlan compara planos de vídeo),
`width`, `height`, `aspectRatio`, `fps`, `rendererAdapter` (ecoado da Composition) e
`durationMs` (duração total da Composition). `plannedContainer` só existe quando o
perfil do catálogo o declara (`mp4`/`webm`); **codec, bitrate e fornecedor não existem
no contrato e não são inventados**.

**Timeline.** Cada etapa traduz um beat validado, sem conteúdo novo: `order`,
`beatId`, `sceneIds` (a relação muitos-para-muitos beat/cena é preservada),
`startMs`, `durationMs`, `endMs` derivado (`startMs + durationMs`),
`narrativeFunction`, `motionIntent`, `transitionIn`, `transitionOut` e, quando
existem no beat, `onScreenText` e `narrationText` — textos nunca alterados. A
timeline é contígua, começa em zero e termina exatamente em `output.durationMs`.
Nenhum asset, prompt ou mídia é inferido.

**Artefatos esperados.** Somente artefatos lógicos, em ordem fixa:
`primary-output`, `captions`, `narration-script`, `execution-report`. Cada um tem
`id`, `kind`, `required`, `logicalName` (nome lógico derivado do `packageId`, sem
caminho absoluto) e `contentType` lógico (`video`, `text/srt`, `text/plain`,
`application/json`). Nenhum arquivo físico é criado nesta etapa; os nomes apenas
declaram o que a execução futura deverá produzir.

**Source references.** Somente IDs e versões de schema dos quatro documentos de
origem — nunca os documentos completos. O validador exige igualdade com os IDs de
topo e versões inteiras positivas.

**packageId determinístico.** Forma legível
`execution-<projectId>-<compositionId>-<outputPlanId>-<beatPlanId>` enquanto couber
em 128 caracteres; acima do limite, canonicalização explícita (JSON com chaves em
ordem fixa, sem espaços) + SHA-256 (`node:crypto`) com prefixo versionado
`execution-v1-`. Sem timestamp, sem aleatoriedade, sem caminho, sem depender da
ordem de propriedades do objeto original. **Este é o packageId do pacote, nunca um
Workflow ID, e não reutiliza o `contentHash` do Temporal** (que permanece fora
desta fatia). O validador rederiva o identificador e rejeita inconsistência
(`EXECUTION_PACKAGE_ID_MISMATCH`).

**Códigos de falha da geração (estáveis).** `PIPELINE_INVALID`,
`PIPELINE_STAGE_BLOCKED`, `REQUIRED_ID_UNAVAILABLE`,
`UNSUPPORTED_OUTPUT_CONFIGURATION`, `DURATION_MISMATCH`,
`INTERNAL_INVARIANT_FAILED`. Nenhum pacote parcial é devolvido em falha.

**Serialização canônica.** A ordem dos campos é implementada explicitamente pelo
contrato (nunca herdada do objeto original); arrays preservam a ordem semântica;
o mesmo pacote produz bytes idênticos e parse + serialização produz os mesmos
bytes. Nenhuma dependência externa de canonical JSON. As fixtures versionadas são
comparadas byte a byte com o gerador em memória, a serialização e a CLI
(`tests/creative-execution-package-e2e.test.ts`), com hashes SHA-256 conferidos.

**Geração transacional da CLI.** Fluxo: carregar todos os casos → validar → criar
pacotes em memória → validar pacotes → serializar → escrever em staging interno →
validar os bytes escritos → promover com rename → preservar a saída anterior em
qualquer falha (backup dos alvos existentes e reversão dos já promovidos). O
output-dir é obrigatório, relativo, estritamente dentro da raiz de confinamento
(lexical e após realpath; symlink externo rejeitado) e só é criado depois de todas
as validações. Nenhum pacote parcial é promovido.

**Contrato da CLI `content:build-execution-packages`.** Flags: `--manifest
<cases-manifest.json>` e `--output-dir <diretorio>` obrigatórios; `--root <raiz>`
opcional (padrão: diretório do manifesto); `--json` opcional. O manifesto de casos
declara `{ schemaVersion: 1, id?, cases: [...] }` com caminhos relativos ao
diretório do manifesto. Exit codes: `0` todos os pacotes gerados · `1` um ou mais
casos inválidos · `2` uso, path, manifesto, arquivo ou JSON inválido · `3` falha de
geração ou validação do pacote · `4` falha de escrita ou promoção. stdout contém
somente o relatório; stderr somente erro sanitizado; zero stack trace e zero
caminho absoluto da máquina.

**Exemplos.** Os dois consumidores reais geram pacotes independentes:
`execution-marca-salao-social-reel-example-instagram-reels-video-social-reel-beat-plan`
(14000 ms, 3 etapas) e
`execution-multitrack-hub-multitrack-social-reel-example-instagram-reels-video-multitrack-social-reel-beat-plan`
(15000 ms, 4 etapas). As fixtures são técnicas: não constituem render, job
executado, campanha aprovada nem autorização de publicação.

**Fronteiras desta fatia.** Tudo interno: o entrypoint público continua exportando
apenas `validateComposition`; subpaths do pacote respondem
`ERR_PACKAGE_PATH_NOT_EXPORTED` (teste de consumidor externo estendido); a CLI fica
fora do tarball; `node:crypto` aparece somente no contrato, para o fallback do
packageId. Nenhum import de `@temporalio/*`, nenhuma regra de marca no núcleo,
nenhum caminho de fixture no domínio, filesystem somente no loader/CLI.

## Executor local simulado v1

**Finalidade.** O pacote técnico responde "o que um executor futuro deverá
consumir?"; o executor local simulado comprova a fronteira entre planejamento e
execução **sem renderização real**: percorre a timeline, valida as etapas,
materializa artefatos textuais previsíveis, registra estados e produz relatório
determinístico. **Pacote não é execução**: o `CreativeExecutionPackage` é a
especificação imutável; a execução simulada é uma verificação do contrato, com
eventos, estados, falha, cancelamento, retomada e hashes. O adaptador `simulation`
**não é um renderer** e não deve ser apresentado como tal; nenhuma mídia é
produzida, nenhum arquivo binário é criado.

| Peça | Onde | Papel |
|---|---|---|
| Contrato do plano | `src/simulated-execution-plan-contract.ts` | `SimulatedExecutionPlan`, steps com operações neutras, `executionId` determinístico |
| Contrato do relatório | `src/simulated-execution-report-contract.ts` | estados, eventos, `SimulatedExecutionReport`, códigos de retomada |
| Compilador puro | `src/create-simulated-execution-plan.ts` | valida o pacote e compila a timeline em steps; resultado discriminado |
| Validadores puros | `src/validate-simulated-execution-plan.ts`, `src/validate-simulated-execution-report.ts` | estrutura + semântica, códigos estáveis |
| Espelhos draft-07 | `schemas/simulated-execution-plan.schema.json`, `schemas/simulated-execution-report.schema.json` | forma estrutural, executados por `ajv` |
| Runner | `src/simulated-execution-runner.ts` | execução sequencial, eventos, artefatos textuais, falha/cancelamento controlados, retomada |
| Serialização canônica | `src/serialize-simulated-execution.ts` | plano, relatório, eventos, manifesto do artefato primário, hashes |
| Writer transacional | `src/simulated-execution-writer.ts` | confinamento, staging, releitura, hashes, backup, promoção com rename, reversão |
| Multicase | `src/simulated-execution-multicase.ts` | agregação pura com contagens por estado e ordem estável |
| CLI interna | `src/simulated-execution-cli.ts`, script `content:simulate-execution` | pacote único ou diretório de pacotes, flags de teste controlado |
| Fixtures canônicas | `examples/simulated-executions/marca-salao/`, `examples/simulated-executions/multitrackhub/` | produzidas pelo próprio executor, comparadas byte a byte |

**Plano.** `schemaVersion: 1`, `executionId`, `packageId`, `caseId`,
`adapter: "simulation"`, `output`, `steps`, `expectedArtifacts`. Cada entrada da
timeline gera quatro etapas na ordem fixa `prepare-scene → apply-text →
apply-motion → finalize-scene`; textos, intenções e IDs são preservados sem
alteração; nenhuma instrução de renderização, comando de ferramenta ou prompt
generativo é criado. O `executionId` é `simulation-<packageId>` até 128 caracteres;
acima do limite, canonicalização + SHA-256 com prefixo `simulation-v1-` (sem
timestamp, random, caminho, máquina, usuário, PID ou variável de ambiente).

**Estados e eventos.** Estados: `pending`, `running`, `completed`, `failed`,
`cancelled`. Eventos: `execution-started`, `step-started`, `artifact-created`,
`step-completed`, `step-failed`, `execution-cancelled`, `execution-completed`,
`execution-failed`. Cada evento carrega somente `sequence` inteira, `type`,
`executionId` e referências opcionais (`stepId`, `artifactId`, `failureCode`);
**nenhum timestamp real** — a ordem vem da sequência e o tempo lógico vem da
timeline do pacote. `cancelled` não é `failed`; `failed` exige `failureCode`;
`completed` exige todos os steps.

**Artefatos simulados.** Somente textuais/JSON, derivados exclusivamente do plano:
`artifacts/primary-output.manifest.json` (descreve logicalName, mediaKind,
dimensões, duração, profile e `simulated: true` — **não cria mídia**),
`artifacts/captions.txt` (textos de tela por janela temporal),
`artifacts/narration-script.txt` (narrações por janela),
`artifacts/execution-summary.txt` (resumo determinístico), além de
`execution-plan.json`, `execution-report.json`, `events.json` e `hashes.json`
(SHA-256 de todos os arquivos gerados, exceto o próprio `hashes.json`). Sem data,
hostname, usuário ou caminho absoluto. Em falha/cancelamento, artefatos cuja
primeira etapa declarante não foi concluída não são materializados.

**Falha e cancelamento controlados.** `failAtStepId` falha a etapa indicada
(`SIMULATED_STEP_FAILURE`): etapas anteriores permanecem concluídas, a etapa falha
não entra em `completedSteps`, etapas posteriores não executam. `cancelAfterSequence`
cancela deterministicamente após N eventos, sem `failureCode` técnico. São opções
explícitas de teste do executor simulado; não pertencem a contratos de produção
futura. Nenhum sleep, timer real, paralelismo ou processo filho.

**Retomada segura.** `checkSimulatedResume`/`resumeSimulatedExecution` retomam
somente com `executionId` e `packageId` iguais, relatório anterior válido, status
`failed` ou `cancelled`, steps concluídos como prefixo do plano e hashes dos
artefatos conferidos. A retomada preserva steps e eventos anteriores (sem
duplicação), executa apenas os steps restantes, continua a sequência de eventos e
indica `resumedFromStatus`. Pacote/plano alterado, hash divergente, status
`completed` ou relatório inválido são rejeitados com códigos próprios
(`REPORT_INVALID`, `EXECUTION_ID_MISMATCH`, `PACKAGE_ID_MISMATCH`,
`STATUS_NOT_RESUMABLE`, `ARTIFACT_HASH_MISMATCH`). Nenhum checkpoint complexo ou
banco local.

**Transação.** O writer serializa tudo em memória, cria staging interno ao destino,
escreve, relê, valida bytes e hashes, faz backup dos alvos existentes, promove com
rename e reverte em falha; o destino anterior fica intacto e o staging é preservado
até o diagnóstico (removido pela CLI após o erro sanitizado). O output-dir é
relativo, estritamente confinado à raiz declarada (lexical + realpath); caminho
absoluto, escape por `..`, symlink externo e arquivo no lugar de diretório são
rejeitados. Zero promoção parcial.

**Multicase.** Pacotes executados sequencialmente, cada um em diretório separado
por `executionId`; uma falha não impede os demais; relatório agregado com contagens
`completed/failed/cancelled` e resumo; zero regra por marca.

**Contrato da CLI `content:simulate-execution`.** Flags: `--package <arquivo>` ou
`--packages-dir <dir>` (exatamente um), `--output-dir <dir>` obrigatório,
`--root <raiz>` opcional (padrão: diretório do pacote ou o diretório de pacotes),
`--json`; teste controlado: `--fail-step <stepId>`, `--cancel-after <sequence>`,
`--resume-from <execution-report.json>` (somente com `--package`). Exit codes:
`0` todas concluídas · `1` uma ou mais não concluídas (falha de step ou
cancelamento) · `2` uso, path, arquivo ou JSON inválido · `3` pacote ou plano
inválido · `4` escrita, promoção ou hash inválido · `5` retomada incompatível.
stdout somente relatório; stderr somente erro sanitizado; zero stack e zero
caminho absoluto.

**Exemplos.** As fixtures canônicas dos dois consumidores (Marca Salão, 12 steps;
Multitrack Hub, 16 steps) são geradas pelo próprio executor e comparadas byte a byte
entre memória, serialização, CLI e fixture (`tests/simulated-execution-e2e.test.ts`),
com hashes SHA-256 conferidos e reexecução com zero diff. Não constituem render,
job executado, campanha aprovada nem autorização de publicação.

**Fronteiras desta fatia.** Tudo interno: entrypoint público inalterado
(`validateComposition` apenas); subpaths do executor simulado respondem
`ERR_PACKAGE_PATH_NOT_EXPORTED`; CLI fora do tarball; filesystem somente no writer
e na CLI; `node:crypto` somente para hashes e para o fallback do `executionId`;
nenhum import de `@temporalio/*`, nenhuma regra de marca no núcleo, nenhum timer,
nenhuma rede, nenhum fornecedor, nenhuma mídia.

## Limites atuais (expressos)

- **Composition v1 implementada apenas como contrato declarativo** (sem áudio, prompts,
  providers, montagem, timeline executável ou geração de assets dentro da composição: a
  tradução temporal é um documento à parte, o `BeatPlan` interno, que também não renderiza
  nada);
- **`BeatPlan` não é superfície pública**: não sai por `composition-validation-api.ts` (o
  entrypoint continua com `validateComposition` e os três tipos já documentados) e não ganha
  subpath em `exports` — `dist/src/beat-plan-contract.js` responde
  `ERR_PACKAGE_PATH_NOT_EXPORTED`. Os módulos internos existem fisicamente no pacote, e as
  CLIs continuam excluídas por `!dist/src/*-cli.*`;
- **`BeatPlan` não se combina com `OutputPlan` nem com Temporal nesta tarefa**: nenhuma peça
  do catálogo de saída ou do resolvedor lê um plano de beats, nada em
  `orchestration/temporal/` foi tocado e nenhum import de `@temporalio/*` existe na `platform`;
- **`BeatPlan` não corrige o que recebe**: não gera beats, não reordena o array, não preenche
  lacuna, não corta beat, não altera a Composition e não verifica a existência física de
  nenhuma evidência em `editorialEvidence` — são identificadores conceituais;
- **Nenhum renderizador foi implementado** (HTML/FFmpeg/HyperFrames/edição: nada adotado;
  `renderer.adapter: "undecided"` é aceito e nenhum adapter precisa estar instalado);
- **HyperFrames não foi instalado** e permanece apenas possibilidade futura atrás de adaptador;
- **Nenhum vídeo é gerado** e nenhum preview/render/upload/publicação existe;
- **Nenhuma ferramenta audiovisual externa foi instalada** por estas fatias (HyperFrames,
  Google Flow, ElevenLabs, FFmpeg, CapCut etc. permanecem não adotados);
- **O espelho JSON Schema expressa só o que o draft-07 declara**: ficam apenas no
  validador TypeScript (implementação de referência) a unicidade de `id` de cena, a soma de
  `durationMs` sem overflow, o vínculo de `format.profile` e `locale` com o ProjectManifest,
  a detecção de nomes sensíveis **por token** (p. ex. `assets/api-secrets.yaml`) e a
  sintaxe completa de `href` pelo parser de URL. O inverso **não** existe: desde as etapas 5 e
  6 o core confere a forma canônica `scheme://host` e o limite da autoridade na string
  original, antes da normalização do parser, então nenhuma estrutura declarada inválida pelo
  schema retorna `valid: true` no validador — e nenhum `@` de caminho, query ou fragmento é
  rejeitado como credencial. A lista completa e testada está em *Regras do schema × regras do
  core* e no corpus classificado;
- **Paridade é estrutural, nunca de decisão**: os 181 casos estruturais exigem o mesmo
  veredicto dos dois motores; os 21 casos semânticos exigem os códigos do validador e
  **registram** o que o schema faz com o mesmo documento. Nada nesta fatia promete que o
  schema resolva vínculo entre documentos;
- **`scenes: []` é aceito** pelos dois motores: a v1 não declara número mínimo de cenas, e
  endurecer isso seria um requisito novo, não uma correção. Continua aceito, documentado e
  coberto por caso explícito no corpus (`scenes vazio (v1 aceita: nenhum minimo declarado)`);
- **Ocorrência local sem causa determinada**: na etapa 4, uma única execução de `npm test` em
  Windows + Node 22.23.4 terminou com `# pass 286 / # fail 6`. Os nomes dos seis testes não
  foram preservados porque a saída foi canalizada para `tail` antes de inspeção; 12 execuções
  seguintes, com saída integral, deram 292/292, e 6 execuções isoladas mais 3 paralelas dos
  testes de CLI não reproduziram a falha. **Nada foi corrigido "por garantia" e não há retry
  automático**: o que existe é a captura completa de TAP + exit code (local e no gate), para
  que a próxima ocorrência venha com diagnóstico — e o passo `Prova do ramo de falha` garante
  que essa captura continue alcançável sob o `errexit` do runner. Ela permanece registrada como
  não diagnosticada; os ajustes da etapa 6 (limite da autoridade do `href` e captura do
  diagnóstico no gate) **não explicam** aquela ocorrência e não foram feitos por causa dela.
  As execuções da etapa 6 — Windows + Node 22.23.4 e Windows + Node 24.19.0, com 308 testes —
  passaram sem falha;
- **`renderer.adapter: "undecided"` e `metadata.status: "approved"` não mudam de sentido**
  com esta correção: o primeiro é um adaptador ainda não escolhido (e produz apenas
  `COMPOSITION_RENDERER_UNDECIDED`), o segundo é estado técnico. Nenhum dos dois significa
  prontidão de produção nem autorização editorial;
- **O catálogo de saída não certifica mídia**: nenhum arquivo de imagem ou vídeo é aberto,
  medido ou comparado; `requiresInspection` (`media-file`, `codec`, `bytes`,
  `audio-streams`/`image-format`, `publication`) nomeia justamente o que continua fora do
  escopo destas fatias;
- **Regra sem fonte confirmada é pendência, nunca limite inventado**: `P-*` aparece em
  `pendingRuleIds` e no diagnóstico `pendencias de fonte:` inclusive no sucesso, e uma regra
  oficial cujos `contexts` não cobrem o contexto declarado produz
  `OUTPUT_PLAN_RULE_NOT_APPLIED` em vez de verificar silenciosamente;
- **A capacidade declarada é observada nesta caixa** (`preset-only` → `canvas-template-mapped`
  → `tool-export-observed`), não é promessa das redes sociais: nenhum perfil afirma o que a
  ferramenta local não exportou ou não tem template;
- **Os exemplos não autorizam publicação** — são fixtures de contrato, não campanhas;
  as fixtures da Multitrack Hub são técnicas e fictícias, coerentes com a identidade
  documentada da marca, e não reutilizam campanha publicada nem dados reais; os
  pacotes de execução são especificações técnicas, não peças renderizadas;
- **O CreativeExecutionPackage não executa nada** — nenhum renderizador, Worker ou
  adaptador foi implementado; o pacote não gera mídia, não cria arquivos físicos de
  saída, não acessa rede e não entra no Temporal; `packageId` não é Workflow ID;
- **O executor local simulado não é renderer** — o adaptador `simulation` verifica o
  contrato e produz somente texto/JSON determinístico; nenhuma mídia, renderização,
  fornecedor, publicação ou Temporal; `executionId` não é Workflow ID;
- **NS-001 não foi alterada** e nenhuma campanha/briefing/hook/roteiro foi tocado;
- **Marca Salão e Multitrack Hub são consumidores, não núcleo** — `platform/src` e
  `platform/schemas` não contêm referência a nenhuma das duas marcas (há teste
  estrutural que garante isso a cada execução, com varredura de independência de
  marca estendida ao segundo consumidor).

## Próximos incrementos possíveis (não compromissos)

- Evolução da Composition (`VisualStyle`, `VisualAnchor`, `AssetManifest` completo,
  `AudioPlan`, `RenderPlan`) — o BeatPlan v1 existe como fatia interna e não muda isso:
  amarrar o plano de beats a plano visual, de assets, de áudio ou de render continua futuro;
- Validator editorial (briefing/roteiro aprovados) e de assets;
- Adaptadores de renderizador (HTML/CSS + FFmpeg como primeiro candidato);
- Preview e renderização reproduzíveis; inspeção e report de artefatos;
- Extração do mínimo reutilizável após o primeiro caso real validado.
