# Devlog — Etapa 6, Agente 1 de 8 (Rótulos de UI parametrizáveis por nicho)

## Contexto

- Worktree isolada: `.workspace/worktrees/etapa6-agente1`.
- Branch: `codex/etapa6-agente1` (a partir de `main` = `8a1b361`, release Etapa 5B).
- Base de leitura: `schemas/brand-kit.schema.json`, `tools/preset_runner.py`,
  `tools/tests/test_preset_runner.py`, os 5 `tenants/*/brand-kit.json` e os
  respectivos `guardrails.json`.
- `contexto_projeto.md` NÃO foi editado na worktree (evita conflito de merge entre os
  8 agentes). Este devlog é a fonte que o consolidador sincroniza via
  `tools/devlog_sync.py`.
- Território editado: `schemas/brand-kit.schema.json`, `tenants/*/brand-kit.json`,
  `tools/preset_runner.py`, `tools/tests/test_preset_runner.py`,
  `.workspace/devlogs/etapa6-agente1.md`.

## Problema

`tools/preset_runner.py` desenhava textos fixos de salão nas cenas `saas-demo`
(`PROFISSIONAIS DO SALAO`, `SERVICOS DISPONIVEIS`, `/BOOKING/[SALONID]`,
`/GESTOR/AGENDA`, `DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO`, `CLIENTE`,
`atendimento`) mesmo para nichos como `estudio-flow` (pilates/yoga) e
`clinica-vital` (saúde). Era preciso parametrizar esses rótulos no contrato
`brand-kit.json`, com fallback 100% retrocompatível para `marca-salao`/`meu-salao`.

## Entregas

### 1. Schema (`schemas/brand-kit.schema.json`)

Nova propriedade **opcional** `uiLabels` (`type: object`, `additionalProperties: false`)
com 7 chaves string (`minLength: 1`):
`teamSectionTitle`, `catalogSectionTitle`, `publicRouteFallback`,
`managerRouteFallback`, `journeyBridgeCaption`, `itemUnitLabel`, `customerLabel`.

- `additionalProperties: false` garante que o validador
  (`tenant_validator.validate_against_schema`) rejeite chaves desconhecidas dentro de
  `uiLabels`.
- Opcional (fora de `required`) → fixtures/brand-kits sintéticos sem `uiLabels`
  continuam válidos.

### 2. Brand-kits (5 tenants) — valores de `uiLabels`

| tenant | teamSectionTitle | catalogSectionTitle | publicRouteFallback | managerRouteFallback | journeyBridgeCaption | itemUnitLabel | customerLabel |
| --- | --- | --- | --- | --- | --- | --- | --- |
| marca-salao | PROFISSIONAIS DO SALAO | SERVICOS DISPONIVEIS | /booking/[salonId] | /gestor/agenda | DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO | atendimento | Cliente |
| meu-salao | PROFISSIONAIS DO SALAO | SERVICOS DISPONIVEIS | /booking/[salonId] | /gestor/agenda | DO AGENDAMENTO DA CLIENTE A AGENDA DO MEU SALAO | atendimento | Cliente |
| estudio-flow | INSTRUTORES DO ESTUDIO | MODALIDADES DISPONIVEIS | /aulas/[studioId] | /gestor/turmas | DA RESERVA DA ALUNA A GRADE DO ESTUDIO | aula | Aluna |
| clinica-vital | ESPECIALISTAS DA CLINICA | PROCEDIMENTOS DISPONIVEIS | /avaliacao/[clinicId] | /gestor/consultas | DA MARCACAO DO PACIENTE A AGENDA DA CLINICA | consulta | Paciente |
| multitrack-hub | CATALOGO DE PROJETOS | FAIXAS E RATEIOS | / | /rateios | DA ORGANIZACAO DOS STEMS AOS RATEIOS | projeto | Musico |

- `marca-salao` NÃO inclui "Meu Salão" (é `forbiddenClaim`) — verificado.
- Todos os rótulos passam pelos `guardrails.json` de cada tenant (auditoria abaixo).

### 3. Refatoração (`tools/preset_runner.py`)

- `DEFAULT_UI_LABELS` (valores de salão) + `_resolve_ui_labels(brand_kit)`:
  mescla defaults com `brand_kit["uiLabels"]`, por chave; chaves ausentes/vazias/tipo
  inválido caem no padrão de salão → retrocompatibilidade total.
- `_render_saas_frame` passou a usar os rótulos resolvidos (normalizados via
  `_norm_text`, compatível com a fonte bitmap 5x7):
  - `PROFISSIONAIS DO SALAO` → `teamSectionTitle`;
  - `SERVICOS DISPONIVEIS` → `catalogSectionTitle`;
  - `/BOOKING`, `/BOOKING/[SALONID]` → `publicRouteFallback`;
  - `/GESTOR/AGENDA` → `managerRouteFallback`;
  - ponte `DO AGENDAMENTO DA CLIENTE A AGENDA DO SALAO` → `journeyBridgeCaption`;
  - `CLIENTE` (passos do hook e resumos) → `customerLabel`;
  - `VALOR ESTIMADO` → `VALOR ESTIMADO POR {itemUnitLabel}` (atendimento/aula/consulta);
  - fallback da rota em `booking-selection` deixou de ser hardcoded
    (`"/booking/[salonId]"`) e passou a usar `publicRouteFallback`.
- **Auditoria de guardrails dos `uiLabels`:** em `run_preset_pipeline`, os rótulos
  resolvidos entram em `texts_to_audit` (`uiLabels.<chave>`) ANTES de qualquer render,
  com `validate_text_against_guardrails(..., check_ui_elements=True)`.
- O manifesto agora registra `"uiLabels"` resolvidos (normalizados) — rastreável e
  testável.

### 4. Testes (`tools/tests/test_preset_runner.py`)

- Nova classe `UiLabelsTest` com **5 testes** (total do arquivo = 13):
  1. `test_ui01` fallback sem `uiLabels` == `DEFAULT_UI_LABELS` (retrocompatível).
  2. `test_ui02` resolução específica de `clinica-vital` e `estudio-flow` (+ fallback parcial por chave).
  3. `test_ui03` guardrail bloqueia `uiLabel` proibido ("Meu Salão" injetado em marca-salao).
  4. `test_ui04` schema rejeita chave desconhecida dentro de `uiLabels`.
  5. `test_ui05` gera frames `saas-demo` reais de clinica-vital e estudio-flow (PNG 1080x1920) e confirma ausência de regressão no marca-salao.
- Ajuste de ambiente (dentro do território): a injeção de `ffmpeg` no `PATH` do teste
  agora resolve a **raiz principal** via `git rev-parse --git-common-dir`, achando o
  ffmpeg compartilhado em `<MAIN_ROOT>/.workspace/tools/ffmpeg` mesmo rodando numa
  worktree (antes dependia de `<worktree>/.workspace/tools/ffmpeg`, inexistente).

## Resultados

- `python tools/tenant_validator.py --all --json` → `ok: true` nos 5 tenants.
- `python -m unittest tools.tests.test_preset_runner tools.tests.test_tenant_contracts -v`
  → **22 testes OK** (8 preset_runner + 5 uiLabels + 9 tenant_contracts), ~88s
  (inclui renders reais FFmpeg de marca-salao saas-demo e multitrack-hub shorts, com e
  sem áudio externo).
- Frames `saas-demo` gerados para `clinica-vital` (`ESPECIALISTAS DA CLINICA`) e
  `estudio-flow` (`INSTRUTORES DO ESTUDIO`) sem regressão no `marca-salao`.
- FFmpeg usado: 9.1-essentials em `<MAIN_ROOT>/.workspace/tools/ffmpeg` (compartilhado,
  fora do versionamento).

## Observações / limitações (fora do escopo deste agente)

- Rótulos singulares no resumo (`PROFISSIONAL:`, `SERVICO:`) NÃO estão entre as 7
  chaves de `uiLabels`; permanecem como estão e não disparam guardrails. Uma futura
  extensão poderia adicionar `professionalLabel`/`serviceLabel`.
- `multitrack-hub` usa preset `shorts-completo`; seus `uiLabels` são preenchidos e
  auditados, mas o render de shorts não consome essas chaves nesta etapa (shorts tem
  vocabulário próprio e não vazava salão).
- `_norm_text` (e `_draw_text`) já aplicam uppercase/transliteração; a normalização é
  idempotente.

## Conformidade

- Trabalho restrito à worktree `.workspace/worktrees/etapa6-agente1`.
- `contexto_projeto.md` não editado (sincronização delegada ao consolidador).
- Working tree da branch limpo ao final; commit na branch `codex/etapa6-agente1`.