# Devlog — Etapa 5B / Agente 4 (integração do QA editorial no pipeline)

> **Data:** 2026-11-20  
> **Branch/worktree:** `codex/etapa5b-agente4` em `.workspace/worktrees/etapa5b-agente4`  
> **Base integrada:** `main` @ `3f8cb1a` (Etapa 5B consolidada: 5 tenants, 10 campanhas)  
> **Escopo:** estágio opcional `editorial_qa` no pipeline mestre, cobertura de teste e suíte do CI

## 1. Contexto

A versão consolidada da Etapa 5B já trazia o `factory_cli.py pipeline` com 9 estágios
(contratos, render, derivados, cards, pacotes, calendário, portal, UTM e release gate),
o `utm_simulator`, o playbook de analytics e os triggers de `01-insta-stories/deliveries/**`.
Esta rodada fecha a integração com o módulo paralelo de QA editorial.

## 2. Alterações

| Arquivo | Mudança |
| --- | --- |
| `tools/factory_cli.py` | novo estágio opcional `editorial-qa` entre `utm` e `release-gate`; resolução via `importlib` com adaptador para `run_editorial_qa`/`audit_editorial_qa`/`run_qa`/`audit`; `counts.editorialQa`; saída humana atualizada |
| `tools/tests/test_factory_cli.py` | `test_02` (render binário) com `skipUnless` quando `ffmpeg`/`ffprobe` ausentes; listas de estágios atualizadas com `editorial-qa`; `editorial-qa` aceito como `ok` ou `skipped` (módulo paralelo) |
| `.github/workflows/local-render-validation.yml` | `tools/tests/test_editorial_qa.py` incluído na suíte explícita do CI |
| `.workspace/devlogs/etapa5-agente5.md` | este relatório |

Contrato assumido para o módulo paralelo (documentado no erro do estágio):

```
tools/editorial_qa.py :: run_editorial_qa(root=".") -> dict
# retorno: {"ok": bool, "totalChecked": int?, "findings": list?, "warnings": int?, "reportPath": str?}
```

Se o módulo não existir, o estágio fica `skipped` e o pipeline segue. Se existir e
retornar `ok: false`, o estágio falha com `EDITORIAL_QA_REPROVADO` e o pipeline
retorna `ok: false` (fail-closed apenas para o módulo presente).

## 3. Evidências

```
$ python -m unittest tools/tests/test_factory_cli.py -v
Ran 6 tests — OK (skipped=1)
# skip: ffmpeg/ffprobe indisponiveis nesta estacao; render binario nao executavel

$ python tools/factory_cli.py pipeline --all --skip-render --json
ok=True
contratos ok · render ok · derivados ok · cards-estaticos ok · pacotes ok
calendario ok · portal ok · utm ok · editorial-qa skipped · release-gate ok
counts: 5 tenants, 10 campanhas, 10 entregas, 10 derivados, 70 cards,
        10 pacotes, 40 slots, 10 campanhas no portal, 40 URLs UTM, 7/7 domínios ok

$ probe com módulo fake (fora do Git, em .workspace/tmp, removido)
ok-path:   editorial-qa ok (totalChecked=10), pipeline ok=True
fail-path: editorial-qa failed (EDITORIAL_QA_REPROVADO), pipeline ok=False
```

## 4. Limitações

- `ffmpeg`/`ffprobe` continuam fora do PATH nesta estação e a worktree não possui
  `.workspace/tools/ffmpeg`; por isso o teste de render binário foi marcado como
  `skip` (permitido pelo contrato desta tarefa). O caminho real roda no CI.
- `tools/editorial_qa.py` e `tools/tests/test_editorial_qa.py` ainda não existem
  nesta branch; o estágio fica `skipped` e a entrada do CI passa a valer assim que
  o módulo do agente paralelo for integrado.

## 5. Handoff

- Branch `codex/etapa5b-agente4` com commit limpo.
- Verificação rápida: `python tools/factory_cli.py pipeline --all --skip-render --json`
  deve listar 10 estágios, com `editorial-qa` em `ok` ou `skipped`.
- Nenhum arquivo fora do território exclusivo foi alterado; `contexto_projeto.md`
  permanece intacto.