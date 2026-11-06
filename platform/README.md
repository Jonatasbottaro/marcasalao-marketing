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
```

`dist/` é **artefato local** gerado pelo build e está ignorado pelo Git
(`platform/.gitignore`). Os exemplos JSON continuam sendo lidos da árvore-fonte
(`platform/examples/projects/`); o caminho informado em `--project` é resolvido em
relação ao diretório atual de execução.

Exit codes da CLI: `0` válido · `1` manifesto inválido (relatório emitido) · `2` erro de
uso, arquivo inexistente ou JSON malformado (mensagem sanitizada, sem stack trace).

## Gate automático (GitHub Actions)

Arquivo: `.github/workflows/platform-validation.yml`.

| Aspecto | Configuração |
|---|---|
| Gatilhos | `pull_request` e `push` **filtrados** por `platform/**` e pelo próprio workflow; `workflow_dispatch` para execução manual |
| Matriz | `ubuntu-latest` + `windows-latest` × Node `22` + `24` — os quatro dentro de `engines: ">=22 <25"` (`fail-fast: false`, para que um ambiente não oculte o veredito dos outros) |
| Cache | `actions/setup-node@v4` com `cache: npm` e `cache-dependency-path: platform/package-lock.json` |
| Ordem | `npm ci` → `npm run clean` → `npm run typecheck` → `npm test`, todas com `working-directory: platform` e `shell: bash` nos dois sistemas |
| Permissões | `contents: read`; nenhum segredo é referenciado no arquivo |
| Diagnóstico | cada passo de verificação grava a saída completa em `platform/gate-logs/` e o passo de testes preserva o **exit code original** (`set -o pipefail` + `exit "$code"`); `actions/upload-artifact@v4` publica os logs **só em falha**, com nome por combinação da matriz |

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
log, não substitui o veredito, e não há retry automático em nenhum passo. Localmente, o mesmo
padrão serve (`npm test > gate-logs/npm-test.tap 2>&1; echo "exit=$?"`); `gate-logs/` está no
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
pelo espelho normativo e o core a aceitava por outra via, porque `new URL()` normaliza
`http:/exemplo.com` e `https:\\exemplo.com`. O validador agora verifica o prefixo
`http(s)://` literalmente, antes de chamar o parser: as duas formas voltam a ser rejeitadas
**pelos dois motores**, com `COMPOSITION_CTA_HREF_INVALID` no core, e figuram como casos
estruturais do corpus. Não sobrou divergência em que o schema declara inválida uma estrutura
que o core aceita como `valid: true`.

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
o validador TypeScript. Não há tabelas duplicadas por arquivo.

| Grupo | O que prova | Quem decide |
|---|---|---|
| `structuralProjectCases` (47) e `structuralCompositionCases` (122) | a regra vive na forma do próprio documento | **os dois precisam coincidir** no veredicto |
| `semanticCases` (21) | vínculo com o ProjectManifest (`projectId`, `locale`, `format.profile`), manifesto inválido, unicidade de `id` de cena, soma de `durationMs` com overflow, nomes sensíveis por token, sintaxe de `href` pelo parser e as heurísticas de warning | **só o TypeScript**; o veredicto do schema para o mesmo documento fica registrado em `schemaAccepts` |

Cada caso carrega nome, documento e (quando inválido) os **códigos exatos** esperados do
validador; os casos semânticos trazem também o projeto contra o qual são validados, o
motivo (`reason`) e os warnings esperados. O motivo da classificação é parte do corpus,
não um comentário solto: os testes de contrato exigem que todo `SemanticReason` documentado
tenha ao menos um caso.

Rodam em `tests/contracts/`:

- `structural-parity.test.ts` — os 169 casos estruturais, veredicto dos dois motores e
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
  execuções, ausência de caminho absoluto/timestamp/stack trace e arquivos intactos.

`npm test` executa tudo (294 testes nesta etapa); `npm run test:contracts` executa
especificamente a verificação de contrato (206 testes) — ambas sobre o JavaScript
compilado em `dist/`.

## Regras textuais e de URL

`isNonEmptyString` (trim) vale para todo campo de texto obrigatório ou opcional: `name`,
`locale`, `timezone`, `brandTheme`, `assetRoot`, `title`, `locale` da composição, `text`,
`alt`, `accessibilityLabel`, `description`, `tags` e `asset.path`. "Apenas espaços" é erro,
não conteúdo.

`content.href` é validado com `new URL()` **como dado**: protocolo precisa ser `http:` ou
`https:` (o parser normaliza a caixa), o hostname precisa existir e `username`/`password`
precisam ser vazios; uma `@` na autoridade também é rejeitada, mesmo sem usuário escrito.
Nenhuma requisição, DNS ou resolução de caminho é feita — nunca.

## Stack e dependências

- TypeScript com sintaxe erasable (sem enums/namespaces), **compilado com `tsc` antes
  da execução** (ESM/NodeNext, target ES2022, saída em `dist/`) — **zero dependências
  de runtime**;
- Validações explícitas escritas à mão (superfície pequena e enumerada); os arquivos
  `schemas/project.schema.json` e `schemas/composition.schema.json` (JSON Schema
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
  divergências conhecidas entre os dois;
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

## Limites atuais (expressos)

- **Composition v1 implementada apenas como contrato declarativo** (sem beats, áudio,
  prompts, providers, montagem, timeline executável ou geração de assets);
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
  sintaxe completa de `href` pelo parser de URL. O inverso **não** existe: desde a etapa 5 o
  core exige a forma canônica `scheme://host` literalmente, então nenhuma estrutura declarada
  inválida pelo schema retorna `valid: true` no validador. A lista completa e testada está em
  *Regras do schema × regras do core* e no corpus classificado;
- **Paridade é estrutural, nunca de decisão**: os 169 casos estruturais exigem o mesmo
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
  que a próxima ocorrência venha com diagnóstico. Ela permanece registrada como não
  diagnosticada;
- **`renderer.adapter: "undecided"` e `metadata.status: "approved"` não mudam de sentido**
  com esta correção: o primeiro é um adaptador ainda não escolhido (e produz apenas
  `COMPOSITION_RENDERER_UNDECIDED`), o segundo é estado técnico. Nenhum dos dois significa
  prontidão de produção nem autorização editorial;
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
