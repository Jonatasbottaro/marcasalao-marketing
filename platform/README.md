# Platform — núcleo modular da Content Factory

Esta pasta contém as fatias implementadas do núcleo modular previsto em
[`docs/decisoes/MKT-VIDEO-001-producao-modular.md`](../docs/decisoes/MKT-VIDEO-001-producao-modular.md),
[`docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md`](../docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md)
e [`docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md`](../docs/decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md):

1. **Primeira fatia** — Manifesto de projeto → validação → relatório estruturado → testes com dois projetos diferentes.
2. **Segunda fatia** — Composition v1 → vínculo entre projeto e composição → validação → relatório estruturado → CLI → testes com dois projetos.

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
```

`dist/` é **artefato local** gerado pelo build e está ignorado pelo Git
(`platform/.gitignore`). Os exemplos JSON continuam sendo lidos da árvore-fonte
(`platform/examples/projects/`); o caminho informado em `--project` é resolvido em
relação ao diretório atual de execução.

Exit codes da CLI: `0` válido · `1` manifesto inválido (relatório emitido) · `2` erro de
uso, arquivo inexistente ou JSON malformado (mensagem sanitizada, sem stack trace).

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
  `schemas/project.schema.json` e `schemas/composition.schema.json` (JSON Schema
  draft-07) são a descrição normativa dos contratos e espelham os validadores, testados
  por suas suítes em `tests/` (além dos testes de portabilidade do build);
- `node:test` nativo para os testes, executados sobre o JavaScript compilado em
  `dist/tests`;
- DevDependencies apenas para o gate de tipos e o build, fixadas: `typescript@5.9.3`
  (Apache-2.0) e `@types/node@24.19.2` (MIT). Nenhum pacote de vídeo, parser YAML ou
  JSON Schema runtime foi adicionado; nenhuma dependência foi adicionada nesta fatia.

## Limites atuais (expressos)

- **Composition v1 implementada apenas como contrato declarativo** (sem beats, áudio,
  prompts, providers, montagem, timeline executável ou geração de assets);
- **Nenhum renderizador foi implementado** (HTML/FFmpeg/HyperFrames/edição: nada adotado;
  `renderer.adapter: "undecided"` é aceito e nenhum adapter precisa estar instalado);
- **HyperFrames não foi instalado** e permanece apenas possibilidade futura atrás de adaptador;
- **Nenhum vídeo é gerado** e nenhum preview/render/upload/publicação existe;
- **Nenhuma ferramenta audiovisual externa foi instalada** por estas fatias (HyperFrames,
  Google Flow, ElevenLabs, FFmpeg, CapCut etc. permanecem não adotados);
- Os **exemplos não autorizam publicação** — são fixtures de contrato, não campanhas;
- **NS-001 não foi alterada** e nenhuma campanha/briefing/hook/roteiro foi tocado;
- **Marca Salão é consumidor, não núcleo** — `platform/src` e `platform/schemas` não
  contêm referência a ele (há teste estrutural que garante isso a cada execução).

## Próximos incrementos possíveis (não compromissos)

- Evolução da Composition (BeatPlan, AssetManifest completo, AudioPlan, RenderPlan);
- Validator editorial (briefing/roteiro aprovados) e de assets;
- Adaptadores de renderizador (HTML/CSS + FFmpeg como primeiro candidato);
- Preview e renderização reproduzíveis; inspeção e report de artefatos;
- Extração do mínimo reutilizável após o primeiro caso real validado.
