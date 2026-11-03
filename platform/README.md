# Platform — núcleo modular da Content Factory (primeira fatia)

Esta pasta contém a **primeira fatia** do núcleo modular previsto em
[`docs/decisoes/MKT-VIDEO-001-producao-modular.md`](../docs/decisoes/MKT-VIDEO-001-producao-modular.md)
e [`docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md`](../docs/decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md):

**Manifesto de projeto → validação → relatório estruturado → testes com dois projetos diferentes.**

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
- Validações explícitas escritas à mão (superfície pequena e enumerada); o arquivo
  `schemas/project.schema.json` (JSON Schema draft-07) é a descrição normativa do
  contrato e espelha o validador, que é testado por 32 casos (além dos testes de
  portabilidade do build);
- `node:test` nativo para os testes, executados sobre o JavaScript compilado em
  `dist/tests`;
- DevDependencies apenas para o gate de tipos e o build, fixadas: `typescript@5.9.3`
  (Apache-2.0) e `@types/node@24.19.2` (MIT). Nenhum pacote de vídeo, parser YAML ou
  JSON Schema runtime foi adicionado; nenhuma dependência foi adicionada nesta fatia.

## Limites atuais (expressos)

- **Implementação de composição ainda não iniciada** (sem cenas, timeline ou composição);
- **Nenhum renderizador foi implementado** (HTML/FFmpeg/HyperFrames/edição: nada adotado);
- **HyperFrames não foi instalado** e permanece apenas possibilidade futura atrás de adaptador;
- **Nenhum vídeo é gerado** e nenhum preview/render/upload/publicação existe;
- Os **exemplos não autorizam publicação** — são fixtures de contrato, não campanhas;
- **NS-001 não foi alterada** e nenhuma campanha/briefing/hook/roteiro foi tocado;
- **Marca Salão é consumidor, não núcleo** — `platform/src` e `platform/schemas` não
  contêm referência a ele (há teste estrutural que garante isso a cada execução).

## Próximos incrementos possíveis (não compromissos)

- Composition (formato, cenas, timeline, textos, mídia, legendas, áudio, CTA);
- Validator editorial (briefing/roteiro aprovados) e de assets;
- Adaptadores de renderizador (HTML/CSS + FFmpeg como primeiro candidato);
- Preview e renderização reproduzíveis; inspeção e report de artefatos;
- Extração do mínimo reutilizável após o primeiro caso real validado.
