### Etapa 6 — Agente 7: coerência de hooks A/B e aderência de uiLabels

- **Data:** 2026-11-20
- **Papel:** Engenheiro Sênior de Qualidade Editorial (Agente 7 de 8, Etapa 6, em paralelo).
- **Branch isolada:** `codex/etapa6-agente7`
- **Worktree:** `<RAIZ>/.workspace/worktrees/etapa6-agente7` (já existia; reutilizada, não recriada, conforme regra 1 do pedido).
- **Base:** `main` @ `8a1b361cfda236ed9cdb553bdd81201b146f9bca` (release da Etapa 5B).
- **Território exclusivo:** `tools/editorial_qa.py`, `tools/tests/test_editorial_qa.py` e `.workspace/devlogs/etapa6-agente7.md`.
- **Protocolo `contexto_projeto.md`:** não editado. Este devlog é a fonte completa para o `devlog_sync.py` na consolidação.

## 1. Partida

O `tools/editorial_qa.py` existente (Etapa 5B, Agente 8) já tinha cinco lentes e a API pública
`run_editorial_qa(root=".", strict=False, tenant=None)`. Antes de alterar, foi confirmado que
os 10 hooks A/B do calendário real são distintos, não vazios e limpos quanto aos guardrails
(30 pares avaliados, zero violações), e que nenhum `brand-kit.json` define `uiLabels` hoje —
portanto as duas novas lentes são no-op no acervo atual e não alteram o resultado das 13
verificações originais.

A API pública foi preservada integralmente: mesma assinatura, mesmo `schemaVersion: 1`, mesmos
códigos de saída (`0` aprovado, `1` reprovado, `2` erro). `CHECK_IDS` passou de 5 para 7 entradas
e `CHECK_NAMES` ganhou os dois rótulos correspondentes; nenhum campo existente foi removido ou
renomeado.

## 2. Novas verificações

### 2.1 `coerencia_hooks_calendario` (lente 6)

Só executa quando `04-legendas/calendario-editorial.json` existe e é legível. Para cada slot com
`tenantId` e `slug`, avalia `hookVarianteA` e `hookVarianteB`:

| Código | Severidade | Condição |
| --- | --- | --- |
| `HOOK_VARIANTE_AUSENTE` | erro | campo ausente, não string ou vazio após `strip()` |
| `HOOK_GUARDRAIL_VIOLACAO` | erro | `validate_text_against_guardrails(texto, guardrails, check_ui_elements=True)` retorna violação |
| `HOOK_VARIANTES_IDENTICAS` | aviso | A e B iguais após `strip()` + `casefold()` |
| `TENANT_INVALIDO` | erro | brand-kit/guardrails do tenant ilegíveis |
| `CALENDARIO_ILEGIVEL` | erro | calendário presente mas inválido |

Os problemas são deduplicados por `(tenant/slug, código, mensagem)` para evitar repetição nas
várias superfícies da mesma campanha, e respeitam o filtro `tenant`. Guardrails são carregados
com cache por execução via `tenant_validator.load_and_validate_tenant(..., strict=False)`.

### 2.2 `aderencia_ui_labels` (lente 7)

Para cada tenant em `tenants/*` com `brand-kit.json` que **defina** `uiLabels`, percorre
recursivamente objetos e listas e valida cada valor textual:

| Código | Severidade | Condição |
| --- | --- | --- |
| `UI_LABELS_TIPO_INVALIDO` | erro | `uiLabels` não é objeto |
| `UI_LABEL_TIPO_INVALIDO` | erro | valor folha não é string |
| `UI_LABEL_VAZIA` | erro | string vazia após `strip()` |
| `UI_LABEL_GUARDRAIL_VIOLACAO` | erro | violação de `forbiddenClaims`/`forbiddenUiElements` |
| `TENANT_INVALIDO` | erro | guardrails do tenant ilegíveis |

Quando `uiLabels` não existe, a lente é aprovada sem problemas. O filtro `tenant` também se
aplica. `validate_brand_kit` sinaliza `uiLabels` como propriedade adicional (schema `additionalProperties: false`),
mas `editorial_qa` usa `strict=False` e consome somente os guardrails, sem reprovar o tenant por isso.

## 3. Arquivos alterados

| Arquivo | Mudança |
| --- | --- |
| `tools/editorial_qa.py` | Docstring atualizada (7 lentes), constantes `CALENDAR_REL`, dois IDs/nomes em `CHECK_IDS`/`CHECK_NAMES`, helpers `_tenant_guardrails`, `_check_calendar_hooks` e `_check_ui_labels`, chamadas das duas lentes em `run_editorial_qa`, descrição da CLI atualizada. |
| `tools/tests/test_editorial_qa.py` | Helpers `_write_json`, `_sandbox_with_calendar`, `_mutate_hooks`, `_add_ui_labels` e 6 novos testes (12 a 17). |
| `.workspace/devlogs/etapa6-agente7.md` | Este relatório completo para consolidação via `devlog_sync.py`. |

## 4. Testes adicionados (6)

1. `test_12_hooks_identicos_sao_aviso` — A == B gera aviso; modo normal aprovado, `--strict` reprova.
2. `test_13_hook_com_termo_proibido_e_erro` — hook com `whatsapp` gera erro e o filtro de tenant isola o problema.
3. `test_14_hook_vazio_e_erro` — `hookVarianteA` em branco gera erro.
4. `test_15_ui_labels_invalidos_sao_erro` — valor vazio, termo proibido e valor não string.
5. `test_16_ui_labels_validos_sao_aprovados` — rótulos válidos, incluindo objeto aninhado.
6. `test_17_acervo_real_novas_lentes_aprovadas` — calendário e brand-kits reais sem problemas nas duas lentes.

Os testes de defeito usam sandbox somente-leitura copiado para `<RAIZ>/.workspace/tmp/editorial-qa/`,
fora do Git; o calendário real é copiado para o sandbox somente nos testes de hooks.

## 5. Evidências

```text
python -m unittest tools/tests/test_editorial_qa.py -v
Ran 19 tests in 21.346s — OK
(13 testes anteriores + 6 novos)

python tools/editorial_qa.py --json
schemaVersion=1; ok=True; checks=7
checkIds=duracao_srt_manifest, legibilidade_mobile, paridade_entregas,
         guardrails_cruzados, integridade_utf8,
         coerencia_hooks_calendario, aderencia_ui_labels
errors=0; warnings=46 (avisos conhecidos de linha longa de SRT)
coerencia_hooks_calendario: status=ok, 0 problemas
aderencia_ui_labels: status=ok, 0 problemas
```

## 6. Limites e governança

- Ferramenta permanece somente leitura: não publica, não agenda, não grava artefatos de campanha.
- Não edita `contexto_projeto.md`, `rastreio-utm.md`, calendário, brand-kits nem matriz UTM.
- Não gera áudio, TTS, música nem faixa sonora (política de vídeo sem áudio).
- Não altera as cinco lentes existentes nem muda a semântica de `strict`/`--tenant`.
- O calendário e os brand-kits reais seguem como estão; nenhum hook ou rótulo foi "corrigido".

## 7. Handoff

Commit realizado apenas nesta branch; consolidação/merge na `main` fica a cargo do titular.
A worktree permanece registrada (remoção exige autorização). Nenhum arquivo relacionado ao
projeto foi criado fora de `<RAIZ>`.
