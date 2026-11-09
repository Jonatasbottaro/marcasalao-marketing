# TEMPORAL-02 — validação de Composition v1 contra ProjectManifest

- Status: PRD em revisão
- Implementação: não iniciada
- Autorização de implementação: não concedida
- Primeiro consumidor previsto: exemplos técnicos integrados do núcleo
- Dependência: TEMPORAL-01, ProjectManifest e Composition v1
- Fora de dependência: R001, OutputPlan e BeatPlan
- Natureza do artefato: exclusivamente documental
- Branch documental: `codex/prd-temporal-02-validacao-composition`
- Base: `3304e82aedf5db59d6507ece6ca20b4df46ac973`

> Este documento planeja. Ele não implementa, não autoriza implementação, não
> altera código, não altera dependências e não produz mídia. `valid: true` continua
> sendo apenas um resultado estrutural — nunca aprovação editorial, gravação,
> agendamento ou publicação.

## 1. Título e identificação

| Campo | Valor |
| --- | --- |
| Identificador | `TEMPORAL-02` |
| Título | Validação de Composition v1 contra ProjectManifest |
| Artefato | PRD técnico, sem código |
| Passo real planejado | `validate-composition` (um único) |
| Incremento anterior | [TEMPORAL-01 — piloto de orquestração com Temporal](./TEMPORAL-01-piloto-de-orquestracao.md) |
| Incremento posterior reservado | TEMPORAL-04 (combinação de planos, prévia, exportação e renderização) |

A numeração TEMPORAL-03 não é criada, reivindicada nem definida por este PRD.

## 2. Status

| Dimensão | Estado |
| --- | --- |
| Documento | PRD em revisão |
| Implementação | não iniciada |
| Autorização de implementação | não concedida |
| Código escrito | nenhum |
| Dependências adicionadas | nenhuma |
| `platform/` alterado | não |
| `orchestration/temporal/` alterado | não |
| CI alterado | não |
| Temporal executado | não |
| Deploy executado | não |
| PR aberta automaticamente | não |

A passagem de "PRD em revisão" para "aprovado" e, depois, para "implementação
autorizada" exige decisão explícita e separada. Revisão textual deste documento não
constitui autorização.

## 3. Referência da main e fontes consultadas

Antes da redação, o estado real do Git foi conferido: repositório na raiz do clone,
working tree limpo, `main` e `origin/main` coincidindo em
`3304e82aedf5db59d6507ece6ca20b4df46ac973`, e nenhum commit novo além da correção
documental pós-merge da PR #7. Confirmou-se também, nesse `HEAD`:

- `ProjectManifest` e `Composition v1` integrados;
- TEMPORAL-01 integrado e aprovado;
- `docs/contexto/` integrado;
- gate Elephant–Goldfish concluído;
- TEMPORAL-02 não iniciado e TEMPORAL-04 reservado;
- R001 e BeatPlan ainda branch-only, sem ancestralidade com a `main`.

Este PRD não assume que a `main` permanece nesse hash. Se a `main` avançar antes de
uma eventual implementação, o novo hash deve ser registrado, os commits novos
inspecionados e a presença dos três artefatos-base confirmada — sem retornar ao hash
`3304e82` e sem reescrever histórico.

### Leituras de origem

Regras e continuidade: [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md),
[README.md](../../README.md), [WORKFLOW.md](../../WORKFLOW.md),
[índice de contexto](../contexto/README.md),
[ESTADO-ATUAL.md](../contexto/ESTADO-ATUAL.md),
[PROXIMOS-PASSOS.md](../contexto/PROXIMOS-PASSOS.md),
[HANDOFF.md](../contexto/HANDOFF.md).

Decisões de arquitetura:
[pipeline criativo modular](../decisoes/MKT-PIPELINE-001-pipeline-criativo-modular.md),
[plataforma multiprojeto](../decisoes/MKT-PLATFORM-001-plataforma-multiprojeto.md).

Piloto anterior:
[especificação TEMPORAL-01](./TEMPORAL-01-piloto-de-orquestracao.md),
[README do pacote Temporal](../../orchestration/temporal/README.md),
[manifest do pacote Temporal](../../orchestration/temporal/package.json),
[Workflow do piloto](../../orchestration/temporal/src/workflows/content-pilot-workflow.ts),
[opções de start do cliente](../../orchestration/temporal/src/client/pilot-start.ts),
[chave do piloto](../../orchestration/temporal/src/pilot-core/pilot-plan.ts),
[Activities do piloto](../../orchestration/temporal/src/activities/pilot-activities.ts).

Núcleo: [README da platform](../../platform/README.md),
[manifest da platform](../../platform/package.json),
[contrato de projeto](../../platform/src/project-contract.ts),
[contrato de Composition](../../platform/src/composition-contract.ts),
[validador de projeto](../../platform/src/validate-project.ts),
[validador de Composition](../../platform/src/validate-composition.ts),
[relatório estruturado](../../platform/src/validation-report.ts),
[CLI de projeto](../../platform/src/validate-project-cli.ts),
[CLI de Composition](../../platform/src/validate-composition-cli.ts),
[schema de projeto](../../platform/schemas/project.schema.json),
[schema de Composition](../../platform/schemas/composition.schema.json),
[projeto de exemplo técnico](../../platform/examples/projects/fixture-project.project.json),
[Composition de exemplo técnico](../../platform/examples/compositions/fixture-project-pilot.composition.json),
[segundo projeto de exemplo](../../platform/examples/projects/marca-salao.project.json),
[segunda Composition de exemplo](../../platform/examples/compositions/marca-salao-pilot.composition.json),
[testes de projeto](../../platform/tests/project-validation.test.ts),
[testes de Composition](../../platform/tests/composition-validation.test.ts).

R001 e BeatPlan foram consultados apenas como referência de fronteira, sem integração
e sem uso de seus contratos como dependência deste PRD.

## 4. Visão

TEMPORAL-02 prova que o piloto Temporal consegue orquestrar uma capacidade real do
núcleo modular sem acoplar Temporal ao núcleo.

O sucesso do incremento não se mede por quantidade de funcionalidade, mas pela
qualidade da fronteira: um Workflow mínimo, uma única Activity real, nenhuma
duplicação de regra de validação e nenhum conhecimento de orquestração dentro da
`platform/`.

## 5. Problema

TEMPORAL-01 usa Activities técnicas puras, mas ainda não consome uma capacidade real
da Content Factory. Suas funções validam um pedido, preparam e finalizam uma
execução simulada; nenhuma delas chama um validador de conteúdo do núcleo. Falta,
portanto, demonstrar que o arranjo "Workflow determinístico + Activity com efeito
externo nulo + núcleo puro" sobrevive ao contato com um contrato real.

Há também um problema de fronteira ainda não resolvido: hoje não existe uma via
pública e estável de importação entre `platform/` e `orchestration/temporal/`. O
PRD registra essa dificuldade como **gate obrigatório** a satisfazer antes da futura
Activity, sem resolvê-la por hipótese (ver seções 18 e 29).

## 6. Oportunidade

Validar uma Composition contra um ProjectManifest é uma operação real,
determística e sem efeito colateral, adequada para a primeira integração:

- os dois contratos já estão na `main`;
- o validador já existe, já tem comportamento definido e já tem testes;
- o retorno é um relatório pequeno, estruturado e com códigos estáveis;
- a operação não lê disco, não acessa rede, não cria arquivo e não muta entradas;
- a operação não depende de fornecedor, modelo, renderer ou serviço remoto;
- a operação exercita exatamente o vínculo entre dois contratos, e não apenas um
  deles isoladamente.

## 7. Decisão do passo real

O PRD escolhe **exatamente um** passo real:

> Validar uma Composition v1 contra um ProjectManifest usando o validador integrado
> no núcleo.

Identificador conceitual da operação: `validate-composition`, coerente com o módulo
`validate-composition.ts` já existente.

O passo deve, na futura implementação:

1. receber um `ProjectManifest`;
2. receber uma `Composition` v1;
3. validar o projeto;
4. validar a estrutura da Composition;
5. verificar o vínculo entre Composition e projeto;
6. produzir o relatório estruturado já definido pelo núcleo;
7. retornar o resultado ao Workflow;
8. não alterar nenhum input;
9. não criar arquivo;
10. não acessar rede.

Não há segunda operação real. Não entram neste incremento OutputPlan, BeatPlan,
perfil social, preview, exportação, renderização, mídia, campanha ou publicação.

### Ponto de integração real

A função exportada pelo módulo interno existente é
`validateComposition(compositionInput, projectInput)`. Ainda não existe uma
fronteira pública e estável entre os pacotes `platform` e `orchestration/temporal`.

```ts
validateComposition(compositionInput: unknown, projectInput: unknown): CompositionValidationReport
```

A ordem dos argumentos é **Composition primeiro, ProjectManifest depois**. Ambos os
parâmetros são atualmente tipados como `unknown`. Essa ordem é a do código e deve
ser respeitada pela Activity; invertê-la produziria relatórios errados sem erro de
tipo, justamente porque o compilador não protege contra a inversão. O teste
obrigatório de paridade com a chamada direta ao núcleo está na seção 26 e é a
mitigação exigida para esse risco.

A função já executa, internamente, `validateProjectManifest(projectInput)`, a
validação estrutural da Composition e as três verificações de vínculo
(`COMPOSITION_PROJECT_ID_MISMATCH`, `COMPOSITION_LOCALE_MISMATCH` e
`COMPOSITION_FORMAT_PROFILE_NOT_ALLOWED`). Portanto os itens 3, 4 e 5 acima são
atendidos por **uma única chamada**, não por três etapas separadas no Workflow.

## 8. Justificativa da escolha

- `ProjectManifest` está integrado à `main`.
- `Composition` v1 está integrada à `main`.
- O validador já possui comportamento e testes de paridade, determinismo, ausência
  de mutação e ausência de acesso externo.
- O resultado é pequeno e estruturado: `CompositionValidationReport` com `valid`,
  `errors`, `warnings`, `summary`, identificadores e métricas derivadas.
- A operação é determinística: o relatório não contém marca de tempo, identificador
  aleatório nem caminho absoluto da máquina.
- A operação não possui efeito colateral.
- A operação não depende de fornecedor.
- A operação permite testar a fronteira entre Temporal e núcleo com um oráculo
  simples: chamar o núcleo diretamente e comparar com o retorno da Activity.
- R001 e BeatPlan continuam branch-only, logo não podem ser dependência.
- TEMPORAL-04 está reservado para combinar planos, prévia e exportação.

`valid: true` permanece um resultado técnico de estrutura; não autoriza conteúdo.

## 9. Alternativas rejeitadas

### Validar apenas ProjectManifest

Rejeitada: pequena demais para provar o vínculo entre contratos. Repetiria, com
outra roupagem, o que as Activities técnicas de TEMPORAL-01 já demonstram.

### Usar OutputPlan

Rejeitada: ainda está branch-only em R001 e não é dependência permitida deste PRD.

### Usar BeatPlan

Rejeitada: ainda está branch-only. Nenhum contrato branch-only entra em TEMPORAL-02.

### Gerar preview ou exportar

Rejeitada: pertence a TEMPORAL-04, conforme a seção 14 da especificação de
TEMPORAL-01, e exigiria mídia, renderer ou efeito de escrita.

### Chamar CLI via subprocesso

Rejeitada como abordagem principal porque:

- adiciona fronteira de processo desnecessária;
- exige parsing de stdout;
- complica portabilidade e timeout;
- oculta o contrato TypeScript;
- aumenta o risco de caminhos absolutos.

Os CLIs existentes (`validate-project-cli.ts` e `validate-composition-cli.ts`)
permanecem válidos para uso humano e para testes de paridade, mas não são a via de
integração do Workflow.

**Recomendação preferencial:** usar a função pura do núcleo por uma única Activity,
assim que o gate de fronteira pública da seção 18 estiver satisfeito.

## 10. Usuários técnicos e consumidores

Consumidores previstos, todos técnicos:

- desenvolvedor do núcleo;
- operador local do pipeline;
- futuro orquestrador da Content Factory;
- testes automatizados.

TEMPORAL-02 **não** é produto para usuário final. Não há persona comercial fictícia,
funil, métrica de engajamento ou promessa de resultado de marketing. Marca Salão
pode aparecer apenas como exemplo de consumidor técnico já presente nos exemplos do
núcleo; o núcleo não contém e não deve conter regra específica de marca.

## 11. Escopo do PRD

Inclui somente:

- contrato de solicitação;
- contrato de resultado;
- Workflow de validação;
- uma Activity real;
- adaptação entre Temporal e o núcleo;
- políticas de timeout;
- políticas de retry;
- política de erro;
- idempotência;
- segurança da history;
- testes;
- observabilidade mínima;
- critérios de aceite;
- plano de implementação futura.

A implementação não é executada nesta tarefa.

## 12. Fora de escopo

- implementar TEMPORAL-02;
- escrever Workflow, Activity ou adaptador;
- alterar `package.json`, lockfile, `tsconfig` ou CI;
- alterar `platform/` ou `orchestration/temporal/`;
- adicionar dependências de qualquer natureza;
- executar Temporal, servidor efêmero, worker ou replay;
- integrar R001 ou BeatPlan;
- criar OutputPlan;
- gerar preview, exportar, renderizar ou gerar mídia;
- usar Qwen, Higgsfield, FFmpeg, renderer ou serviço de mídia;
- alterar campanha, NS-001 ou qualquer conteúdo editorial;
- publicar conteúdo ou criar campanha;
- deploy;
- TEMPORAL-04;
- atualizar `ESTADO-ATUAL.md`, `PROXIMOS-PASSOS.md`, `HANDOFF.md` ou TEMPORAL-01.

Também fora de escopo: banco, Redis, armazenamento remoto, SDK de IA, fila
adicional, API HTTP e stack de observabilidade externa.

## 13. Arquitetura conceitual

```
  cliente (preflight)
      |  input pequeno, versionado, sem dado sensível
      |  valida tamanho, schemaVersion e padrões proibidos ANTES do start
      |
      +-- A. rejeição de preflight ---> erro local do cliente
      |                                 (sem start; sem execução;
      |                                  sem CompositionValidationWorkflowResult)
      v
  start do cliente
      |
      +-- B. conflito de start -------> TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT
      |                                 (sem nova execução; sem resultado;
      |                                  execução original intacta)
      v
  CompositionValidationWorkflowInput  --->  [ history do Temporal ]
      |
      v
  validateCompositionWorkflow            (determinístico; sem I/O; sem platform)
      |  proxyActivities + 1 chamada
      v
  validateCompositionActivity           (ÚNICA fronteira com o núcleo)
      |  validateComposition(composition, project)
      v
  platform/  ->  validateProjectManifest + estrutura + vínculos
      |  CompositionValidationReport
      v
  C. resultado do domínio ------------> CompositionValidationWorkflowResult
      |                                 status valid | invalid
      |                                 validation presente; failureCode nulo
      |                                 completedSteps ["validate-composition"]
      |
      +-- D. falha de execução --------> CompositionValidationWorkflowResult
                                        status failed; validation nulo
                                        failureCode obrigatório
                                        completedSteps []
```

Invariantes de camada:

| Camada | Conhece Temporal? | Conhece marca? | Efeito externo |
| --- | --- | --- | --- |
| `platform/` (núcleo) | não | não | nenhum |
| Activity | sim | não | nenhum |
| Workflow | sim | não | nenhum |
| Cliente | sim | não | start do Workflow |

A `platform/` não importa `@temporalio/*`, não conhece task queue, não conhece
Workflow ID e não é alterada por TEMPORAL-02 em sua lógica de validação. O
Workflow não importa a `platform/` diretamente: a Activity é a fronteira.

## 14. Contrato de entrada proposto

Nome conceitual: `CompositionValidationWorkflowInput`.

Contrato pequeno e versionado, com campos mínimos:

| Campo | Tipo | Observação |
| --- | --- | --- |
| `schemaVersion` | número | Versão do **contrato de solicitação**, distinta do `schemaVersion` dos documentos do núcleo |
| `requestId` | string estável | Compõe o Workflow ID; sem timestamp e sem aleatoriedade |
| `project` | `ProjectManifest` | Documento técnico completo, sem dado pessoal |
| `composition` | `Composition` v1 | Documento técnico completo, sem dado pessoal |

### Impacto de persistir os documentos na history

Antes de confirmar o desenho, é obrigatório considerar que os argumentos do Workflow
são serializados e persistidos na history. As duas opções foram avaliadas:

#### Opção A — documentos completos no input do Workflow

Vantagens:

- sem leitura de arquivo pela Activity;
- totalmente reprodutível pela history;
- mais simples para testes;
- sem caminho local.

Riscos:

- conteúdo integral persiste na history;
- crescimento do payload;
- dados potencialmente sensíveis;
- limite prático da history.

#### Opção B — referências imutáveis resolvidas pela Activity

Exemplo conceitual: `projectRef`, `compositionRef`, `contentHash`.

Vantagens:

- payload pequeno;
- menor exposição na history.

Riscos:

- exige armazenamento ou resolução externa;
- exige política de imutabilidade;
- cria efeito externo e uma segunda fronteira;
- ainda não existe no núcleo.

### Recomendação para TEMPORAL-02

Preferir **Opção A**, apenas para documentos técnicos pequenos e sem dados pessoais,
com limites explícitos de tamanho. Não introduzir armazenamento externo nesta etapa.

Limites do piloto, a validar no cliente antes do `start`:

| Grandeza | Limite |
| --- | --- |
| `ProjectManifest` serializado | máximo de 64 KiB |
| `Composition` serializada | máximo de 256 KiB |
| envelope completo | máximo de 384 KiB |

### Método conceitual de medição

```ts
Buffer.byteLength(JSON.stringify(value), "utf8")
```

A medição é aplicada **separadamente** a `project`, a `composition` e ao envelope
completo. A serialização é parte do preflight: não é uma conversão tolerante a
perdas. Registros obrigatórios:

- os valores são **limites conservadores do piloto**, não limites do produto;
- **não equivalem ao tamanho final codificado pelo Temporal**, que inclui
  codificação de payload, metadados e demais eventos da history;
- valores não serializáveis são **rejeitados**, não omitidos em silêncio;
- ciclos são **rejeitados**;
- `BigInt` é **rejeitado**;
- a medição dos exemplos reais integrados é **obrigatória antes da implementação**;
  se ela tornar os valores inadequados, o ajuste deve ser proporcional e
  justificado, nunca removido silenciosamente.

A Opção B fica registrada como caminho de evolução, não como dívida a saldar neste
incremento.

## 15. Política de history

Registro explícito:

- os argumentos do Workflow são persistidos na history;
- a validação dentro da Activity ocorre **depois** da persistência;
- dados sensíveis não podem ser enviados ao Workflow;
- a fronteira do cliente deve validar tamanho e padrões proibidos antes do `start`;
- nenhuma credencial;
- nenhum token;
- nenhum arquivo local de variáveis de ambiente (configuração dotenv);
- nenhum caminho absoluto;
- nenhum dado pessoal;
- nenhum conteúdo de campanha real;
- nenhum asset binário;
- nenhuma mídia.

Quatro planos distintos, que não devem ser confundidos:

| Plano | Conteúdo | Controlado por |
| --- | --- | --- |
| History | argumentos do Workflow, argumentos e resultado da Activity | decisão de desenho do input (Opção A) e limites |
| Relatório sanitizado | `CompositionValidationReport` e campos derivados | contrato de resultado |
| Logs | apenas campos permitidos da seção 24 | política de observabilidade |
| Inputs da Activity | documentos técnicos já persistidos | assinatura da Activity |

**Um relatório sanitizado não apaga a history.** Nenhuma sanitização posterior
remove o que já foi persistido no evento de início do Workflow. A única mitigação
eficaz é a pré-validação no cliente, antes do `start`. Esta é a mesma ressalva já
registrada no README de TEMPORAL-01.

## 16. Contrato de resultado proposto

Nome conceitual: `CompositionValidationWorkflowResult`.

| Campo | Tipo | Observação |
| --- | --- | --- |
| `schemaVersion` | número | Versão do contrato de resultado |
| `requestId` | string | Eco do input |
| `projectId` | string ou nulo | Eco do relatório |
| `compositionId` | string ou nulo | Eco do relatório |
| `status` | `valid` \| `invalid` \| `failed` | Classificação da execução |
| `validation` | `CompositionValidationReport` ou nulo | Presente em `valid` e `invalid` |
| `completedSteps` | lista estável | Regra fixa na seção "completedSteps" abaixo |
| `failureCode` | string ou nulo | Obrigatório somente em `failed` |

### `valid`

- validação executada;
- relatório do núcleo com `valid: true`;
- `failureCode` nulo.

### `invalid`

- validação executada;
- relatório do núcleo com `valid: false`;
- **não é falha técnica**;
- **está fora da Retry Policy da Activity**; não sofre retry;
- `failureCode` nulo.

### `failed`

- falha técnica da Activity ou do Workflow **em execução já iniciada**;
- `validation: null` quando nenhum `CompositionValidationReport` foi recebido;
- `failureCode` obrigatório;
- `completedSteps: []` enquanto nenhum relatório foi recebido.

### Classificação das quatro vias

#### A. Rejeição de preflight

- antes do `start`;
- erro local do cliente;
- sem execução;
- sem `CompositionValidationWorkflowResult`.

Casos:

- envelope malformado;
- `schemaVersion` do envelope incompatível;
- input acima do limite;
- padrão sensível detectado.

Esses casos **não iniciam Workflow**, **estão fora da Retry Policy da Activity**
e **não produzem `CompositionValidationWorkflowResult`**. Não são `failed`,
porque não há execução a classificar. Os códigos correspondentes estão na seção 23.

#### B. Conflito de start

- tentativa de iniciar `workflowId` já existente;
- sem nova execução;
- erro classificado pelo cliente como
  `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT`;
- sem `CompositionValidationWorkflowResult`;
- a execução original permanece intacta;
- `completedSteps` não se aplica ao start recusado.

Não é `status: failed`, não é erro da Activity e não entra na Retry Policy da
Activity. `WorkflowIdReusePolicy.REJECT_DUPLICATE` e
`WorkflowIdConflictPolicy.FAIL` permanecem preservados (seção 20).

#### C. Resultado do domínio

- execução iniciada;
- `status: valid` ou `status: invalid`;
- `validation` presente, com `CompositionValidationReport`;
- `failureCode: null`;
- `completedSteps: ["validate-composition"]`.

Inclui **qualquer** relatório do núcleo com `valid: false`:

- `ProjectManifest` inválido;
- Composition inválida;
- `projectId` incompatível;
- `locale` incompatível;
- `format.profile` não permitido;
- demais códigos `PROJECT_*` ou `COMPOSITION_*`.

Esses casos **não lançam exceção**, **não entram em `nonRetryableErrorTypes`**,
**não sofrem retry** e **estão fora da Retry Policy da Activity**. São um
resultado normal de domínio, não uma falha de orquestração.

#### D. Falha de execução

- execução iniciada;
- falha transitória esgotada, `StartToCloseTimeout` esgotado ou falha inesperada
  não retryable;
- `status: failed`;
- `validation: null`;
- `failureCode` obrigatório;
- `completedSteps: []` enquanto nenhum relatório foi recebido.

A Retry Policy da Activity (seção 21) separa esses casos em dois tratamentos:

- **retryable até `maximumAttempts: 2`**:
  `TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE` e `StartToCloseTimeout`;
- **não retryable**: `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`, quando lançado como
  `ApplicationFailure` com `nonRetryable=true`.

Somente essas duas condições retryable podem produzir nova tentativa. A colisão
de Workflow ID pertence à via B, não a esta via.

### completedSteps

```text
valid:
  ["validate-composition"]

invalid:
  ["validate-composition"]

failed antes de receber o relatório:
  []

timeout:
  []
```

O passo só é concluído quando a Activity **devolve** `CompositionValidationReport`.
Não marcar como concluído apenas porque a Activity começou. A lista não cresce com
warnings, erros ou tentativas de retry. Em `failed` por `StartToCloseTimeout`
esgotado, o resultado mantém `validation: null` e `completedSteps: []`. Em
conflito de start (via B), `completedSteps` não se aplica, porque nenhuma execução
foi iniciada.

O resultado deve **reutilizar ou encapsular** o `CompositionValidationReport`, sem
reinterpretar, renomear ou remapear seus códigos (`COMPOSITION_*`, `PROJECT_*`). A
Activity não duplica o validador: ela não reimplementa regra, não reconstrói o
relatório e não cria um "relatório próprio" divergente.

## 17. Workflow proposto

Nome conceitual: `validateCompositionWorkflow`.

Fluxo mínimo:

1. aceitar input já pré-validado pelo cliente;
2. chamar uma única Activity real, `validateCompositionActivity`;
3. receber o relatório do núcleo;
4. classificar `valid` ou `invalid`; em falha técnica, classificar `failed` com
   `failureCode`;
5. retornar resultado estruturado.

O Workflow não deve:

- importar `platform/` diretamente;
- validar JSON Schema;
- inspecionar arquivos;
- ler disco;
- acessar rede;
- criar relatório próprio divergente;
- alterar a Composition;
- chamar uma segunda capacidade real.

A classificação de falhas técnicas segue o padrão neutro já usado em TEMPORAL-01:
`ApplicationFailure` e `TimeoutFailure` são convertidos em sinal neutro.
`nonRetryableErrorTypes` contém **apenas**
`TEMPORAL_COMPOSITION_ACTIVITY_FAILED`, lançado como `ApplicationFailure` com
`nonRetryable=true`. **`nonRetryableErrorTypes` não controla `TimeoutFailure`**:
`StartToCloseTimeout` não entra nessa lista e pode gerar a segunda tentativa,
até `maximumAttempts: 2`. Ao esgotar as duas tentativas sem conclusão, o Workflow
classifica `status: failed`, `failureCode: TEMPORAL_COMPOSITION_TIMEOUT`,
`validation: null` e `completedSteps: []`. A conversão de falhas inesperadas da
Activity está registrada na seção 18. A colisão de Workflow ID é conflito de
start do cliente (via B): sem nova execução, sem
`CompositionValidationWorkflowResult` e fora da Retry Policy da Activity. Nenhum
código `PROJECT_*` ou `COMPOSITION_*` entra nessa lista: relatório com
`valid: false` é `status: invalid`, não exceção. O Workflow permanece
determinístico para permitir replay.

O preflight acontece **antes** do Workflow: envelope malformado,
`schemaVersion` incompatível, payload acima do limite e padrão sensível são
rejeitados pelo cliente sem iniciar execução. O Workflow só recebe input já
pré-validado e nunca vê um erro de preflight como `failed`.

`completedSteps` segue a regra fixa da seção 16: `["validate-composition"]` em
`valid` e `invalid`; `[]` em `failed` antes de receber o relatório, inclusive
timeout esgotado, com `validation: null`. O Workflow não inventa sucesso e não
produz resultado para conflito de start.

## 18. Activity real proposta

Nome conceitual: `validateCompositionActivity`.

Responsabilidade:

- receber `ProjectManifest` e `Composition`;
- chamar a função exportada pelo módulo interno, por meio do entrypoint público
  definido no gate abaixo;
- retornar `CompositionValidationReport`;
- não executar CLI;
- não chamar subprocesso;
- não acessar filesystem;
- não acessar rede;
- não criar output;
- não alterar inputs.

Origem real da função, conforme o código consultado:
`platform/src/validate-composition.ts` exporta `validateComposition`, e
`platform/src/validation-report.ts` define `CompositionValidationReport`. A Activity
chama `validateComposition(composition, project)` — nessa ordem — e devolve o
relatório sem transformação. Isso descreve um módulo interno, **não** uma API
pública entre pacotes.

### Tratamento planejado de falhas inesperadas

Decisão de implementação futura, **não implementada neste PRD**: falhas
inesperadas capturadas pela fronteira da Activity devem ser convertidas em
`TEMPORAL_COMPOSITION_ACTIVITY_FAILED`, com:

- `ApplicationFailure`;
- `nonRetryable=true`;
- mensagem fixa e sanitizada;
- sem payload;
- sem caminho absoluto;
- sem stack trace no resultado;
- sem conteúdo bruto da exceção.

Falhas explicitamente simuladas como transitórias usam
`TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE`, com comportamento retryable
até `maximumAttempts: 2`. A distinção é feita na fronteira da Activity, não no
Workflow e não no núcleo. O resultado final permanece `status: failed` com
`failureCode` obrigatório, `validation: null` e `completedSteps: []`.

Pseudocódigo ilustrativo mínimo, sem código executável:

```text
falha inesperada capturada
  -> ApplicationFailure(TEMPORAL_COMPOSITION_ACTIVITY_FAILED,
                        nonRetryable=true, mensagem_fixa_sanitizada)

falha transitória simulada
  -> ApplicationFailure(TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE)
  -> retry até maximumAttempts=2
```

### Gate obrigatório antes da futura Activity

A fronteira pública deixa de ser uma dependência informal e passa a ser um **gate
obrigatório**, a satisfazer antes de escrever a Activity:

1. definir o entrypoint público mínimo da `platform`;
2. definir a forma de consumo compilado pelo pacote Temporal;
3. preservar a `platform` sem dependência Temporal;
4. impedir import relativo de arquivos internos;
5. validar o build em checkout limpo;
6. validar portabilidade em Ubuntu e Windows.

Alternativas permitidas, **a decidir explicitamente** — nenhuma é escolhida de
forma silenciosa por este PRD:

- pacote local;
- workspace;
- artefato compilado.

Proibido como solução:

- import de `platform/src` por caminho relativo;
- import de `dist` sem contrato de build;
- duplicação do validador;
- mover o validador para `orchestration/`.

### Dependência real de implementação (não resolvida por hipótese)

Não existe hoje uma fronteira pública e estável de importação entre os pacotes:

- `platform/package.json` não declara `exports`, `main`, `types` nem `files`, e não
  possui dependências de runtime;
- não há `package.json` na raiz, workspaces npm, arquivo de workspace pnpm nem
  configuração de monorepo;
- `orchestration/temporal/tsconfig.json` inclui apenas `src/**/*.ts` e
  `tests/**/*.ts`, sem project references nem path aliases para `platform/`;
- a única menção cruzada existente está em um teste de fronteira, que localiza o
  diretório da `platform/` por URL relativa apenas para varrer arquivos — não é um
  import de runtime.

A forma exata é decisão em aberto (seção 31, item 4). Este PRD não escolhe, não
instala e não escreve essa configuração. O gate acima é condição de aceite da
implementação, não autorização para executá-la.

## 19. Idempotência

A Activity é naturalmente idempotente se:

- os inputs forem imutáveis;
- o validador for puro;
- nenhum arquivo for criado;
- nenhum estado externo for alterado.

Chave conceitual:

```
requestId + projectId + compositionId + contentHash
```

### Decisão sobre `contentHash`

Recomendação geral de desenho: calcular hash no cliente antes do `start`, usar
SHA-256 dos documentos serializados de forma canônica, não calcular hash com ordem
instável, incluir o hash na identificação da solicitação e **nunca** usar o hash
como substituto de validação.

**Para TEMPORAL-02, `contentHash` não entra.** Não existe hoje canonicalização JSON
no núcleo; inventar um algoritmo improvisado neste PRD criaria uma fonte silenciosa
de divergência entre cliente e Activity. Assim:

- não implementar algoritmo de canonicalização neste incremento;
- registrar a necessidade como decisão em aberto;
- TEMPORAL-02 usa `requestId` único e comparação estrutural nos testes;
- canonicalização formal fica reservada para incremento posterior.

A chave conceitual completa permanece documentada como destino, mas a
idempotência prática deste incremento repousa em: `requestId` único,
`WorkflowIdReusePolicy.REJECT_DUPLICATE`, `WorkflowIdConflictPolicy.FAIL`, input
imutável e validador puro.

## 20. Workflow ID

Formato recomendado:

```
composition-validation-<requestId>
```

Alternativa considerada:
`composition-validation-<projectId>-<compositionId>-<requestId>`.

Avaliação:

| Critério | Formato recomendado | Alternativa |
| --- | --- | --- |
| Legibilidade | suficiente | alta |
| Tamanho | curto e previsível | cresce com os identificadores |
| Exposição de identificadores | mínima | expõe projeto e composição |
| Colisão | evitada por `requestId` único | evitada, porém redundante |
| Reexecução | recusada explicitamente | recusada explicitamente |

Preservar, sem alteração:

- `WorkflowIdReusePolicy.REJECT_DUPLICATE`;
- `WorkflowIdConflictPolicy.FAIL`;
- `workflowId` previsível;
- recusa em execução aberta;
- recusa após conclusão;
- nenhum timestamp;
- nenhuma aleatoriedade.

A colisão ocorre na **operação de start do cliente** (via B): nenhuma nova
execução é iniciada, não há novo `CompositionValidationWorkflowResult`, o cliente
devolve ou imprime `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT`, a execução
original permanece intacta e `completedSteps` não se aplica ao start recusado.
Não é `status: failed`, não é erro da Activity e fica **fora da Retry Policy da
Activity**. Não reutilizar silenciosamente Workflow ID concluído; a recusa é
comportamento esperado e testado, não um erro a esconder.

## 21. Retries

Como a Activity é local, pura e curta, para o primeiro passo real:

| Parâmetro | Valor |
| --- | --- |
| `maximumAttempts` | 2 |
| `initialInterval` | 1 segundo |
| `backoffCoefficient` | 2 |
| `maximumInterval` | 2 segundos |

`maximumAttempts: 2` significa **uma repetição** após a primeira tentativa.

Justificativa:

- resultado de validação é determinístico e não gera retry;
- falha técnica transitória e `StartToCloseTimeout` podem repetir uma vez;
- não existe rede nem serviço remoto;
- três tentativas seriam pouco úteis nesta operação pura.

### Retryable até maximumAttempts=2

- `TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE`;
- `StartToCloseTimeout`.

Um `StartToCloseTimeout` na primeira tentativa **pode gerar a segunda tentativa**.
`startToCloseTimeout` permanece em **5 segundos** e `maximumAttempts` permanece em
**2**. `nonRetryableErrorTypes` **não controla `TimeoutFailure`**: timeout não é
`ApplicationFailure` e não entra nessa lista.

### Não retryable

- `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`, lançado como `ApplicationFailure` com
  `nonRetryable=true`.

É o único código em `nonRetryableErrorTypes`. Falhas inesperadas da Activity são
convertidas nesse código conforme a seção 18, em **uma tentativa**, com mensagem
fixa e sanitizada, sem payload, sem caminho absoluto, sem stack trace no resultado
e sem conteúdo bruto da exceção.

### Fora da Retry Policy da Activity

- erros do preflight;
- relatórios `invalid`;
- colisão de Workflow ID.

A colisão é conflito de start do cliente (via B): sem nova execução, sem
`CompositionValidationWorkflowResult`, sem `status: failed` e sem
`completedSteps` aplicável. O cliente devolve ou imprime
`TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT` e a execução original permanece
intacta. Preflight e `invalid` tampouco são erros da Activity.

### Resultado após duas tentativas sem conclusão

Depois de duas tentativas sem conclusão por `StartToCloseTimeout`, o Workflow
classifica:

```text
status: failed
failureCode: TEMPORAL_COMPOSITION_TIMEOUT
validation: null
completedSteps: []
```

O mesmo formato vale para falha transitória esgotada e para falha inesperada não
retryable, com seus respectivos `failureCode`. `TEMPORAL_COMPOSITION_TIMEOUT`
**não entra em `nonRetryableErrorTypes`**.

### Atenção

Uma Composition semanticamente inválida deve produzir `status: invalid`. Não deve
falhar a Activity como erro técnico.

## 22. Timeouts

| Parâmetro | Valor |
| --- | --- |
| `startToCloseTimeout` da Activity | 5 segundos |

A operação é uma chamada de função pura sobre documentos já em memória; 5 segundos
é folga ampla e preserva o padrão de TEMPORAL-01. `startToCloseTimeout` continua
em **5 segundos** e `maximumAttempts` continua em **2**. Um `StartToCloseTimeout`
pode gerar a segunda tentativa; depois de duas tentativas sem conclusão, o
Workflow classifica `status: failed`, `failureCode:
TEMPORAL_COMPOSITION_TIMEOUT`, `validation: null` e `completedSteps: []`
(seção 21). `TEMPORAL_COMPOSITION_TIMEOUT` não entra em
`nonRetryableErrorTypes` e `nonRetryableErrorTypes` não controla
`TimeoutFailure`. Não há `scheduleToCloseTimeout` adicional, nem polling, nem
heartbeat, nem timeout encadeado neste incremento.

## 23. Códigos de falha

Poucos códigos estáveis, todos de **orquestração**:

| Código | Fase | Quando | Retry |
| --- | --- | --- | --- |
| `TEMPORAL_COMPOSITION_INPUT_INVALID` | preflight | envelope malformado ou `schemaVersion` do envelope incompatível | sem start |
| `TEMPORAL_COMPOSITION_INPUT_TOO_LARGE` | preflight | qualquer limite de payload excedido | sem start |
| `TEMPORAL_COMPOSITION_SENSITIVE_INPUT` | preflight | padrão sensível detectado antes do `start` | sem start |
| `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT` | start do cliente | `workflowId` já existente em execução aberta ou reuso de ID concluído | não aplicável à Retry Policy da Activity |
| `TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE` | Activity/Workflow iniciado | falha explicitamente simulada como transitória | **sim**, até 2 tentativas; `failed` ao esgotar |
| `TEMPORAL_COMPOSITION_ACTIVITY_FAILED` | Activity/Workflow iniciado | falha inesperada convertida na fronteira da Activity | não |
| `TEMPORAL_COMPOSITION_TIMEOUT` | Activity/Workflow iniciado | `StartToCloseTimeout` persistente após duas tentativas | **sim**, até 2 tentativas; `failed` ao esgotar |

Os três primeiros são **A. Rejeição de preflight**: não iniciam Workflow, não
produzem `CompositionValidationWorkflowResult` e não são lançados pela Activity.
`TEMPORAL_COMPOSITION_SENSITIVE_INPUT` permanece exclusivamente como erro do
preflight.

O quarto código é **B. Conflito de start**: ocorre na operação de start do
cliente, nenhuma nova execução é iniciada, não há novo
`CompositionValidationWorkflowResult`, o cliente devolve ou imprime o código, a
execução original permanece intacta e `completedSteps` não se aplica ao start
recusado. Não é `status: failed` e não entra na Retry Policy da Activity.

Os três últimos pertencem à **D. Falha de execução** quando as tentativas se
esgotam ou a falha é não retryable: ocorrem em execução já iniciada e produzem
`CompositionValidationWorkflowResult` com `status: failed`, `validation: null`,
`failureCode` obrigatório e `completedSteps: []` enquanto nenhum relatório foi
recebido. Falha transitória que passa na segunda tentativa produz resultado da
via C, não `failed`. `TEMPORAL_COMPOSITION_TIMEOUT` **não entra em
`nonRetryableErrorTypes`** e `nonRetryableErrorTypes` **não controla
`TimeoutFailure`**.

Não duplicar os códigos de validação do núcleo. Os `errors` e `warnings` de
`CompositionValidationReport` permanecem com os códigos existentes (`COMPOSITION_*`,
`PROJECT_*`), intactos e sem tradução. Nenhum código `PROJECT_*` ou `COMPOSITION_*`
aparece nesta tabela nem em `nonRetryableErrorTypes`.

Distinção central, em **quatro vias**:

- **A. Rejeição de preflight** — antes do start; erro local do cliente; sem
  execução; sem `CompositionValidationWorkflowResult`;
- **B. Conflito de start** — `workflowId` já existente; sem nova execução; erro
  classificado pelo cliente; sem `CompositionValidationWorkflowResult`;
- **C. Resultado do domínio** — execução iniciada; `valid` ou `invalid`;
  `validation` presente; `failureCode: null`;
  `completedSteps: ["validate-composition"]`;
- **D. Falha de execução** — execução iniciada; falha transitória esgotada,
  timeout esgotado ou falha inesperada não retryable; `status: failed`;
  `validation: null`; `failureCode` obrigatório; `completedSteps: []`.

**Somente falha transitória e StartToCloseTimeout podem produzir nova tentativa,
limitados a maximumAttempts=2.** Preflight, `invalid` e colisão de Workflow ID
ficam fora da Retry Policy da Activity.

## 24. Observabilidade

Campos permitidos em logs:

`workflowId`, `requestId`, `projectId`, `compositionId`, `operation`, `status`,
`activity`, `attempt`, `failureCode`, `errorCount`, `warningCount`.

`errorCount` e `warningCount` são contagens derivadas do relatório, não o conteúdo
dos erros. `operation` é o literal `validate-composition`.

Não registrar:

- documento completo;
- texto completo das cenas;
- CTA;
- href;
- caminho de asset;
- dados pessoais;
- tokens;
- payload integral.

Sem OpenTelemetry nesta etapa. Sem stack externa, sem exporter, sem dashboard, sem
métricas de negócio. O log é texto estruturado mínimo, suficiente para correlacionar
uma execução com seu resultado.

## 25. Segurança

- Pré-validação obrigatória no cliente **antes** do `start`, porque a history já
  terá persistido os argumentos quando a Activity executar.
- Documentos estritamente técnicos, sem dado pessoal, sem conteúdo de campanha real
  e sem asset binário.
- Limites de payload aplicados pelo método da seção 14, não por contagem de
  caracteres de campos isolados.
- Nenhuma credencial, nenhum token, nenhuma chave, nenhum cookie, nenhum arquivo
  de configuração privada, nenhum caminho absoluto e nenhuma URI de esquema de
  arquivo local.
- Nenhum valor de fixture de segurança é reproduzido neste documento; em
  particular, nenhum valor usado nos testes de TEMPORAL-01 é copiado para cá.
- Todas as ocorrências de termos como "token", "credencial" ou "chave" neste PRD
  são **proibições ou exemplos lexicais**, sem qualquer valor associado.
- Sanitização do relatório não é promessa de apagamento da history (seção 15).
- `platform/` continua sem dependência de runtime e sem import de `@temporalio/*`.
- Nenhuma publicação, agendamento ou criação de campanha decorre deste PRD.

### Pré-validação de conteúdo sensível

A pré-validação **não é um scanner universal de segredos**. É uma lista finita e
testável de rejeições, executada antes do `start`:

- rejeita **chaves conhecidas** de configuração sensível;
- rejeita **URLs com credenciais** embutidas;
- rejeita **caminhos absolutos**;
- rejeita **arquivos sensíveis conhecidos** (por exemplo, configuração local de
  ambiente);
- aplica **heurísticas adicionais com testes de falso positivo**;
- **nunca ecoa o valor rejeitado** — nem em mensagem de erro, nem em log, nem em
  relatório.

Texto normal de cena **não deve ser recusado apenas** por conter palavras como
"token", "senha" ou "credencial" em contexto editorial. A heurística deve
distinguir ocorrência lexical de dado sensível real; caso contrário, o preflight
rejeitaria uma Composition tecnicamente válida **antes do start**, sem produzir
qualquer `CompositionValidationWorkflowResult` de execução iniciada.

`TEMPORAL_COMPOSITION_SENSITIVE_INPUT` permanece **A. Rejeição de preflight**: sem
start, sem retry, **fora da Retry Policy da Activity** e sem
`CompositionValidationWorkflowResult` (seções 16, 21 e 23).

## 26. Testes propostos

Exigidos na futura implementação — não executados nesta tarefa.

### Contrato e cliente

- input válido;
- envelope malformado;
- `schemaVersion` do envelope incompatível;
- input acima do limite;
- padrão sensível;
- cada rejeição de preflight **não inicia Workflow**, **não produz resultado de
  execução iniciada** e **não ecoa o valor rejeitado**;
- Workflow ID previsível;
- mesma entrada produz mesmas opções de start;
- colisão em execução aberta e reuso após conclusão recusados (detalhes em
  "Colisão" abaixo).

### Medição dos limites

- `project`, `composition` e envelope medidos separadamente;
- valores não serializáveis rejeitados;
- ciclos rejeitados;
- `BigInt` rejeitado;
- medição dos exemplos reais registrada antes da implementação;
- heurística de conteúdo sensível não rejeita texto normal de cena que contenha
  termos como "token", "senha" ou "credencial" em contexto editorial (teste de
  falso positivo).

### Activity

- Composition válida retorna relatório com `valid: true`;
- Composition inválida retorna relatório com `valid: false`;
- `ProjectManifest` inválido retorna relatório inválido;
- incompatibilidade de `projectId`;
- incompatibilidade de `locale`;
- `format.profile` não permitido;
- inputs não alterados;
- nenhuma escrita;
- nenhuma rede;
- Activity chamada duas vezes produz relatórios equivalentes.

### Workflow

- `status: valid`;
- `status: invalid`;
- `status: failed`;
- todo relatório com `valid: false` (projeto inválido, Composition inválida,
  `projectId`, `locale`, `format.profile` e demais códigos do núcleo) produz
  `invalid`, inclui `CompositionValidationReport`, mantém `failureCode: null`,
  **não lança exceção**, **não entra em `nonRetryableErrorTypes`**, **não sofre
  retry** e fica **fora da Retry Policy da Activity**;
- **somente falha transitória e StartToCloseTimeout podem produzir nova
  tentativa, limitados a maximumAttempts=2**;
- `TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE` pode passar na segunda
  tentativa e, se persistir, para após duas;
- `TEMPORAL_COMPOSITION_ACTIVITY_FAILED` é `ApplicationFailure` com
  `nonRetryable=true`, em uma tentativa, sem retry e com mensagem fixa e
  sanitizada;
- colisão de Workflow ID é conflito de start do cliente (via B): sem nova
  execução, sem `CompositionValidationWorkflowResult` e fora da Retry Policy da
  Activity (seção "Colisão");
- `StartToCloseTimeout` esgotado produz `status: failed`,
  `failureCode: TEMPORAL_COMPOSITION_TIMEOUT`, `validation: null` e
  `completedSteps: []` (seção "Timeout");
- `completedSteps` = `["validate-composition"]` em `valid` e `invalid`; `[]` em
  `failed` antes de receber o relatório e em timeout;
- o passo não é marcado como concluído apenas porque a Activity começou;
- resultado preserva os códigos do núcleo;
- replay sem nondeterminismo.

### Colisão

- primeira execução inicia;
- segunda tentativa com o mesmo `workflowId` é recusada;
- nenhuma segunda execução é criada;
- o cliente classifica `TEMPORAL_COMPOSITION_WORKFLOW_ID_CONFLICT`;
- nenhuma `CompositionValidationWorkflowResult` é produzida pela tentativa
  recusada;
- a execução original permanece intacta;
- `completedSteps` não se aplica ao start recusado.

### Timeout

- primeira tentativa sofre `StartToCloseTimeout`;
- a segunda tentativa ocorre;
- timeout persistente para após `maximumAttempts: 2`;
- resultado final da execução: `status: failed`,
  `failureCode: TEMPORAL_COMPOSITION_TIMEOUT`, `validation: null` e
  `completedSteps: []`.

### Falha inesperada

- falha inesperada capturada na fronteira da Activity é convertida em
  `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`;
- uma tentativa;
- sem retry;
- mensagem fixa e sanitizada, sem payload, sem caminho absoluto, sem stack trace
  no resultado e sem conteúdo bruto da exceção.

### Falha transitória

- pode passar na segunda tentativa;
- se persistir, para após duas tentativas;
- nunca ultrapassa `maximumAttempts: 2`.

### Invalid

- permanece resultado de domínio;
- nenhuma exceção;
- nenhuma tentativa adicional.

### Fronteira

- `platform/` não importa Temporal;
- `orchestration/` não duplica o validador;
- nenhuma CLI via subprocesso;
- nenhuma referência a R001;
- nenhuma referência a BeatPlan;
- nenhuma mídia;
- nenhum fornecedor.

### Portabilidade

- Node 22;
- Ubuntu;
- Windows;
- CI existente ampliado ou gate separado, conforme decisão de implementação.

### Paridade com o núcleo

Para **cada caso do corpus definido para TEMPORAL-02**, comparar o retorno da
Activity com a chamada direta a `validateComposition(composition, project)`:
mesmos `valid`, `errors`, `warnings`, `summary` e campos derivados. O corpus é o
conjunto de casos de teste versionado neste incremento; não há promessa de
exaustividade universal. Este é o teste que impede a duplicação silenciosa de
regras e protege contra a inversão da ordem dos argumentos.

## 27. Métricas de sucesso

Métricas técnicas observáveis, sem métrica comercial e sem SLA de produção
inventado:

- **todos os casos do corpus definido para TEMPORAL-02** retornam o mesmo `valid`,
  `errors`, `warnings`, `summary` e campos derivados que a chamada direta ao núcleo;
  o corpus é versionado e não representa promessa de cobertura universal;
- zero divergência de códigos entre Activity e núcleo;
- zero mutação dos inputs;
- zero acesso externo;
- zero arquivo criado;
- replay aprovado;
- colisão recusada no start, sem nova execução e sem
  `CompositionValidationWorkflowResult`;
- CI verde em Ubuntu e Windows;
- nenhum import de Temporal em `platform/`;
- nenhum uso de OutputPlan ou BeatPlan;
- payload dentro dos limites definidos;
- **somente falha transitória e StartToCloseTimeout podem produzir nova
  tentativa, limitados a maximumAttempts=2**;
- `TEMPORAL_COMPOSITION_ACTIVITY_FAILED` com `nonRetryable=true` é não
  retryable, em uma tentativa e com mensagem sanitizada;
- timeout esgotado é `failed` com `TEMPORAL_COMPOSITION_TIMEOUT`,
  `validation: null` e `completedSteps: []`;
- `invalid` nunca sofre retry e fica fora da Retry Policy da Activity;
- preflight não inicia e fica fora da Retry Policy da Activity;
- `completedSteps` não se aplica ao start recusado;
- `nonRetryableErrorTypes` não controla `TimeoutFailure`.

## 28. Riscos e mitigações

### History com conteúdo sensível

Mitigação: pré-validação no cliente; documentos técnicos; limites; proibição de
dados pessoais; testes de não vazamento.

### Acoplamento de `orchestration/` a arquivos internos da `platform/`

Mitigação: export público mínimo; contrato documentado; teste de fronteira.

### Duplicação da validação

Mitigação: Activity chama o validador real; paridade entre chamada direta e
Activity.

### Classificação incorreta da Retry Policy

Mitigação: **somente falha transitória e StartToCloseTimeout podem produzir nova
tentativa, limitados a maximumAttempts=2**. `invalid` permanece resultado normal
de domínio, fora da Retry Policy da Activity. `TEMPORAL_COMPOSITION_ACTIVITY_FAILED`
é `ApplicationFailure` com `nonRetryable=true`, em uma tentativa, com mensagem
sanitizada. `TEMPORAL_COMPOSITION_TIMEOUT` não entra em `nonRetryableErrorTypes`
e `nonRetryableErrorTypes` não controla `TimeoutFailure`. Preflight não inicia;
colisão de Workflow ID é conflito de start, sem nova execução e sem
`CompositionValidationWorkflowResult`.

### Aumento excessivo da history

Mitigação: limites de payload; um único passo; sem mídia; sem outputs grandes.

### TEMPORAL-04 antecipado

Mitigação: proibir OutputPlan, BeatPlan, preview e exportação.

### Dependência de branch pública

Mitigação: usar somente elementos integrados na `main`; R001 e BeatPlan fora.

### Ordem invertida dos argumentos do validador

Mitigação: teste de paridade com chamada direta e assinatura explicitamente
documentada na seção 7; os dois parâmetros são `unknown`, então o compilador não
protege contra inversão.

## 29. Dependências

Existências permitidas, já na `main`:

- `orchestration/temporal/` e seu pacote isolado;
- SDK Temporal TypeScript já integrado (`@temporalio/client`, `@temporalio/common`,
  `@temporalio/worker`, `@temporalio/workflow` e `@temporalio/testing` em versão
  exata `1.25.0`);
- a função exportada pelo módulo interno `platform/src/validate-composition.ts`
  (`validateComposition`) e o tipo `CompositionValidationReport`, ambos **ainda sem
  fronteira pública e estável entre os pacotes**;
- `ProjectManifest` e `Composition` v1;
- exemplos técnicos integrados dos dois contratos, usados como primeiro consumidor.

Não adicionar no planejamento: banco, Redis, armazenamento remoto, SDK de IA, Qwen,
Higgsfield, renderer, FFmpeg, serviço de mídia, fila adicional ou API HTTP.

**Dificuldade real de importação:** não há fronteira pública e estável entre os
pacotes (sem `exports`/`main`/`types` na `platform`, sem workspaces na raiz, sem
project references ou aliases no `tsconfig` do Temporal). Isso está registrado como
**gate obrigatório** na seção 18 e como decisão em aberto na seção 31. Não é
resolvido por hipótese, por import relativo de `platform/src` nem por caminho
relativo disfarçado.

## 30. Roadmap do PRD

Cinco etapas futuras, sem estimativa de data:

| # | Etapa | Esforço | Depende de |
| --- | --- | --- | --- |
| 1 | **Gate obrigatório de fronteira pública** (seção 18): entrypoint mínimo, consumo compilado, build em checkout limpo e portabilidade | pequeno | decisão em aberto 4; autorização de implementação |
| 2 | Contrato de entrada e pré-validação no cliente (tamanho, `schemaVersion`, padrões proibidos) | pequeno | etapa 1; decisões 1, 2 e 3 |
| 3 | Activity real, chamando o núcleo sem CLI nem subprocesso | pequeno | etapas 1 e 2 |
| 4 | Workflow e cliente (Workflow ID, políticas de reuse/conflict, resultado estruturado) | médio | etapa 3; decisões 5, 6 e 7 |
| 5 | Testes, replay, CI e **gate Elephant–Goldfish obrigatório** antes da integração na main | médio | etapa 4; decisões 8 e 9 |

Esforço classificado qualitativamente; nenhuma etapa é classificada como grande
porque o incremento tem um único passo real. A etapa 5 é a mais sensível, pois
envolve replay, portabilidade em dois sistemas operacionais e o gate independente
da seção 31. Nenhuma etapa está autorizada, iniciada ou agendada por este
documento.

## 31. Decisões em aberto

| # | Decisão | Recomendação deste PRD |
| --- | --- | --- |
| 1 | Documentos completos ou referências | Documentos completos (Opção A), com limites; referências ficam para incremento posterior |
| 2 | Limites finais de payload | Manter 64 KiB / 256 KiB / 384 KiB e confirmar por medição dos exemplos técnicos antes da implementação |
| 3 | Canonicalização e `contentHash` | Não incluir `contentHash` em TEMPORAL-02; usar `requestId` único e comparação estrutural nos testes; reservar canonicalização formal para depois |
| 4 | Export público da `platform/` | Satisfazer o **gate obrigatório da seção 18** antes da Activity; escolher explicitamente entre pacote local, workspace ou artefato compilado; proibir import relativo de `platform/src`, import de `dist` sem contrato de build, duplicação do validador e mudança do validador para `orchestration/` |
| 5 | Política definitiva de retry | `maximumAttempts: 2`; retryable: `TEMPORAL_COMPOSITION_ACTIVITY_TRANSIENT_FAILURE` e `StartToCloseTimeout` (um timeout pode gerar a 2ª tentativa); não retryable: `TEMPORAL_COMPOSITION_ACTIVITY_FAILED` como `ApplicationFailure` com `nonRetryable=true`; fora da Retry Policy: preflight, `invalid` e colisão de Workflow ID; timeout esgotado = `failed` + `TEMPORAL_COMPOSITION_TIMEOUT` + `validation: null` + `completedSteps: []`; `nonRetryableErrorTypes` não controla `TimeoutFailure` |
| 6 | Formato do resultado | Encapsular `CompositionValidationReport` sem remapear códigos; `failureCode` somente em `failed`; colisão de Workflow ID é conflito de start e não produz `CompositionValidationWorkflowResult`; `completedSteps` não se aplica ao start recusado |
| 7 | Estratégia de logs | Apenas os 11 campos permitidos da seção 24; sem stack externa |
| 8 | Necessidade de novo gate Elephant–Goldfish | **Executar gate Elephant–Goldfish após a implementação de TEMPORAL-02 e antes de sua integração na main.** Gate obrigatório, não opcional; não simular aprovação |
| 9 | Atualização posterior de `docs/contexto/` | Somente após PRD aprovado e integrado; `ESTADO-ATUAL.md` e `PROXIMOS-PASSOS.md` não são alterados agora |

Nenhuma escolha crítica fica escondida para a implementação decidir sozinha.

### Escopo do gate Elephant–Goldfish

O gate independente deve revisar:

- fronteira pública;
- ordem dos argumentos;
- paridade;
- history;
- payload;
- quatro vias;
- `invalid` versus `failed`;
- retries;
- replay;
- isolamento do núcleo;
- ausência de mídia e fornecedores.

**Este gate não é executado nesta tarefa.** A recomendação acima é de
planejamento; não há implementação, execução nem aprovação simulada.

## 32. Critérios de aceite

O PRD é considerado completo quando:

- contém apenas um passo real (`validate-composition`);
- `ProjectManifest` e `Composition` v1 estão tratados como integrados;
- R001, OutputPlan e BeatPlan estão explicitamente fora;
- TEMPORAL-04 está preservado;
- não há implementação, código, dependência nova nem alteração de CI;
- não há mídia nem fornecedor;
- não há autorização automática de implementação;
- a history é tratada explicitamente, com a distinção entre sanitização, history,
  logs e inputs da Activity;
- as **quatro vias** estão separadas e sem sobreposição: **A. Rejeição de
  preflight**, **B. Conflito de start**, **C. Resultado do domínio** e
  **D. Falha de execução**;
- nenhum caso de `invalid` aparece em lista de erros não retryable da Activity;
- **somente falha transitória e StartToCloseTimeout podem produzir nova
  tentativa, limitados a maximumAttempts=2**;
- `TEMPORAL_COMPOSITION_ACTIVITY_FAILED` com `nonRetryable=true` é o único
  código em `nonRetryableErrorTypes`, em uma tentativa, com mensagem fixa e
  sanitizada, sem payload, sem caminho absoluto, sem stack trace e sem conteúdo
  bruto da exceção;
- `TEMPORAL_COMPOSITION_TIMEOUT` não entra em `nonRetryableErrorTypes` e
  `nonRetryableErrorTypes` não controla `TimeoutFailure`;
- timeout esgotado produz `status: failed`,
  `failureCode: TEMPORAL_COMPOSITION_TIMEOUT`, `validation: null` e
  `completedSteps: []`;
- colisão de Workflow ID não produz `CompositionValidationWorkflowResult`, não é
  `status: failed`, não inicia nova execução e deixa a execução original intacta;
- preflight, `invalid` do domínio e colisão de Workflow ID estão explicitamente
  fora da Retry Policy da Activity;
- `completedSteps` está definido para `valid`, `invalid`, `failed` sem relatório e
  timeout, com a regra de conclusão vinculada ao retorno do relatório; não se
  aplica ao start recusado;
- o método de medição dos limites e as rejeições de serialização estão definidos;
- a Activity chama a função do módulo interno do núcleo pela ordem correta de
  argumentos, com teste obrigatório de paridade sobre o corpus definido;
- a terminologia não afirma que já existe API pública entre pacotes;
- o **gate obrigatório de fronteira pública** está registrado antes da Activity,
  com alternativas a decidir e soluções proibidas;
- o **gate Elephant–Goldfish** está recomendado após a implementação e antes da
  integração na main, sem execução nesta tarefa;
- `platform/` não conhece Temporal;
- a dificuldade real de importação entre pacotes está registrada, sem solução
  hipotética;
- os três status, os sete códigos, os limites, os retries, os timeouts e o
  Workflow ID estão definidos;
- os links relativos são válidos;
- o documento não contém valores sensíveis nem dados pessoais.

Para a **futura implementação**, o aceite técnico é o conjunto de métricas da
seção 27 e os testes da seção 26, com CI verde e replay aprovado. Nada disso foi
executado nesta tarefa.

## 33. Autorização

| Item | Estado |
| --- | --- |
| Elaboração deste PRD | executada, exclusivamente documental |
| Aprovação deste PRD | não concedida |
| Autorização de implementação | **não concedida** |
| Execução de Temporal | não autorizada |
| Geração de mídia | não autorizada |
| Publicação, agendamento ou campanha | não autorizada |
| Deploy | não autorizado |
| Abertura automática de PR | não autorizada |

A revisão e eventual integração deste documento não implicam autorização para as
etapas do roadmap. Qualquer implementação de TEMPORAL-02 depende de autorização
específica, nova e explícita, registrada em separado. Até lá, este arquivo é
planejamento e nada mais.
