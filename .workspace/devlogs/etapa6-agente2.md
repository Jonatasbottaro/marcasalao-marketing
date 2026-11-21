# Etapa 6 — Agente 2 — Quebra mobile determinística de SRT (46 avisos → 0)

**Data:** 2026-11-20
**Papel:** Engenheiro Sênior de Pós-Produção e Qualidade de Legendas (Agente 2 de 8, paralelo)
**Branch:** `codex/etapa6-agente2`
**Worktree:** `.workspace/worktrees/etapa6-agente2` (já existente, base `8a1b361` = `main`)
**Raiz da estação:** `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`

> `contexto_projeto.md` não foi tocado; este relatório é a fonte para o
> `devlog_sync.py` na consolidação. `camp-saas-demo-estudio-flow-002` não foi
> criado nem alterado (não existe em `02-reels-shorts/deliveries/`).

---

## 1. Problema reproduzido

```
python tools/editorial_qa.py --all --strict --json   -> exit 1
ok: false | campanhas: 10 com problemas | 0 erros | 46 avisos
lente legibilidade_mobile: 46 x SRT_LINHA_LONGA
```

Linhas entre 49 e 82 caracteres (teto mobile = 48) distribuídas pelas 10
entregas. Cada `manifest.json` guarda `artifacts.srt.sha256`/`bytes`, então o
hash e o tamanho precisam acompanhar qualquer reformatação.

## 2. Motor `tools/srt_formatter.py` (novo, 100% stdlib)

API implementada:

- `wrap_srt_cue_text(text, max_chars=48, max_lines=2) -> str`
  - normaliza espaços, preserva palavras/pontuação/acentos;
  - corte preferencial depois de pontuação (`, . ; : ! ? — –`), depois antes
    de conjunção (` e `, ` ou `, ` mas `, ` que `, ` para `, ` com `…), por
    fim no espaço mais próximo do ponto médio;
  - entre candidatos válidos (`len <= max_chars` nos dois lados) escolhe o
    mais equilibrado;
  - palavra isolada maior que o teto é cortada em pedaços seguros
    (`_hard_cut`, sem loop);
  - conteúdo maior que `max_lines * max_chars` é preservado integralmente com
    mais linhas, sempre `len(linha) <= max_chars`.
- `format_srt_content(srt_text, max_chars=48, max_lines=2) -> (str, dict)`
  - copia índices e timestamps literalmente; reúne o corpo de cada cue e
    re-quebra; valida com `srt_validate` antes de devolver; estatísticas de
    antes/depois por linha.
- `format_delivery_srts(root=".", max_chars=48, update_manifests=True,
  tenant=None, slug=None, dry_run=False) -> dict`
  - descobre `02-reels-shorts/deliveries/<tenant>/<slug>/<slug>.srt`;
  - grava sempre em LF puro (`\n`) e atualiza `artifacts.srt.sha256/bytes`
    (e `files.srt` quando presente), preservando vídeo, narração e storyboard;
  - `dry_run=True` não grava nada (usado pelo `--check-only`);
  - filtros por tenant/campanha e contenção de path (regex de slug + realpath
    sob a raiz).
- CLI:
  `python tools/srt_formatter.py [--all | --tenant <id> [--campaign <slug>]]
  [--max-chars 48] [--check-only] [--root <raiz>] [--json]`
  - `--check-only`: exit 1 se houver linha acima do teto; nunca grava.

## 3. Resultado por campanha (antes → depois)

`bytes` permaneceu igual porque a quebra troca um espaço (1 byte) por LF
(1 byte); o formatador recalcula o SHA-256 sempre.

| Tenant | Campanha | Max linha antes | Max linha depois | Bytes | Novo SHA-256 do `.srt` |
| --- | --- | ---: | ---: | ---: | --- |
| clinica-vital | camp-saas-demo-clinica-vital-001 | 74 | 47 | 606 | `7ead3171cfd5b06365a1ee043caa416191d5d95a09e2886fd3e5182449a743cc` |
| clinica-vital | camp-saas-demo-clinica-vital-002 | 82 | 47 | 638 | `7ddaeecfced5e4abe475018e1af0e13d12ae32ac63591026a2780a9324afa303` |
| estudio-flow | camp-saas-demo-estudio-flow-001 | 73 | 46 | 572 | `771a38c5c77e10cb38e6cb37ddf88592b7303b8e9b5290d4c501d6fed317be1a` |
| marca-salao | camp-saas-demo-marca-salao-001 | 63 | 47 | 496 | `14b560ff6667789c892acad515aa6625c7fb0b47e5cbbf1587c2f07bc7710ff8` |
| marca-salao | camp-saas-demo-ns001-agenda-001 | 68 | 44 | 584 | `85a7ce46d868677c581b2829627cb7f64a80f0f80a47a656c4fc775be91f21e8` |
| meu-salao | camp-saas-demo-meu-salao-001 | 63 | 47 | 492 | `bd04bd659a960000565161a8d3368c6802e84641e456bcd3339dd5aaa0685898` |
| meu-salao | camp-saas-demo-meu-salao-002 | 70 | 47 | 573 | `2c2babf3abc64ed5fb0b4728ddfbf461a0e1c4f4381572a26280fb67730be5f7` |
| multitrack-hub | camp-shorts-completo-multitrack-001 | 62 | 47 | 444 | `88c9f93934efe07ad195c8225fb66b6f48dc407ec1e2b55a8a7ac2e8f76a4582` |
| multitrack-hub | camp-shorts-rateios-002 | 75 | 44 | 516 | `daeb5d71ef29ce8be3a21844ca1a72e6341d935a307a3eed0049b9ba0da58791` |
| multitrack-hub | camp-shorts-stems-workflow-003 | 71 | 43 | 488 | `901df302c3e8db10ca46387f0047a2d4645d808f9637f4f175ea4ff715a81e93` |

Totais do formatter: **10 campanhas alteradas, 10 manifestos sincronizados,
46 linhas longas antes, 0 depois**. Segunda execução: `changed: 0`.

## 4. Auditorias finais

```
python tools/editorial_qa.py --all --strict --json   -> exit 0, ok: true
  problemas: 0 erros, 0 avisos | checks: 5 ok, 0 warn, 0 fail
python tools/release_audit.py --strict --json        -> exit 0, ok: true
  7/7 domínios ok | 0 erros, 0 avisos | 10/10 entregas, 10/10 pacotes
```

## 5. Testes

`tools/tests/test_srt_formatter.py` (11 testes): quebra equilibrada 48/2,
preservação de índices/timestamps/acentos, idempotência, `--check-only` sem
escrita, sync de manifesto (artifacts + files; demais hashes intactos), LF
puro, 10 campanhas reais (≤48 e hash íntegro), filtros tenant/campanha,
contenção de path, CLI `--json`, palavra única acima do teto.

```
python -m unittest tools/tests/test_srt_formatter.py tools/tests/test_srt_validate.py \
  tools/tests/test_editorial_qa.py tools/tests/test_release_audit.py -v
-> Ran 56 tests ... OK
```

## 6. Desvios declarados (necessários para o critério `ok: true`)

1. **`04-legendas/pacotes-publicacao/**/checklist-publicacao.json` (10 arquivos)**
   — fora do território nominal desta tarefa, mas o `release_audit` cruza
   `checklist.media[kind=srt].sha256` com o arquivo em disco. Atualizei
   cirurgicamente **apenas** `sha256` (e `bytes`, quando divergente) da entrada
   `kind: "srt"`; vídeo, narração e storyboard foram verificados
   programaticamente como idênticos ao HEAD. Sem isso, `release_audit` fica
   `pacotes_sociais: HASH_DIVERGENTE` para as 10 campanhas.
2. **`tools/tests/test_editorial_qa.py`** — também fora do território nominal.
   Três testes codificavam o baseline antigo de 46 avisos:
   - `test_01` esperava `legibilidade_mobile: warn`; agora espera `ok` e 0 avisos;
   - `test_02` substituía uma frase longa que deixou de existir; passou a usar
     o helper `_set_cue_body` (independente do texto atual);
   - `test_10` esvaziava um cue por frase literal; passou a esvaziar o cue por
     índice com o mesmo helper.
   O restante da suíte não foi alterado.
3. **`dry_run`** foi adicionado como parâmetro opcional da API (além da
   assinatura pedida) para implementar `--check-only` sem gravar disco.

## 7. Arquivos alterados

- Novos: `tools/srt_formatter.py`, `tools/tests/test_srt_formatter.py`,
  `.workspace/devlogs/etapa6-agente2.md`.
- Modificados: 10 `.srt` + 10 `manifest.json` em `02-reels-shorts/deliveries/`;
  10 `checklist-publicacao.json`; `tools/tests/test_editorial_qa.py`.
- `contexto_projeto.md` e `camp-saas-demo-estudio-flow-002` intocados.
- Commit local na `codex/etapa6-agente2`; sem push.