# Etapa 5B — Agente 2 (rodada 2) — static_cards cwd-independent + validação do publish_pack

**Data:** 2026-11-20
**Papel:** Engenheiro Sênior de Automação Editorial (Agente 2, paralelo)
**Branch/worktree:** `codex/etapa5b-agente2` em `.workspace/worktrees/etapa5b-agente2`
**Base:** `3f8cb1a` — "chore(release): conclui Etapa 5B (5 tenants, 10 campanhas, ffmpeg portatil e handoff)" (= `main` no momento da sessão)
**Raiz da estação:** `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`

> Nota de nomenclatura: o pedido citava `.workspace/devlogs/etapa5-agente3.md`,
> mas esse arquivo pertence ao Agente 3 (onboarding `clinica-vital`) e já está
> versionado. Para não destruir trabalho de outro agente, este relatório foi
> gravado em `etapa5-agente2b.md`, seguindo a convenção `etapa5-agente1b.md`.

---

## 1. Diagnóstico — falha de caminho relativo no subprocesso

Os testes de CLI executavam:

```python
subprocess.run([sys.executable, "tools/static_cards.py", "--root", ROOT, ...], cwd=ROOT)
```

O script era relativo ao cwd. Reprodução do defeito a partir de um cwd
diferente do checkout (`.workspace/worktrees`):

```
returncode = 2
can't open file '...\.workspace\worktrees\tools\static_cards.py':
[Errno 2] No such file or directory
```

Ou seja: qualquer harness que rode o unittest de outro diretório quebra a
chamada, mesmo com `--root` absoluto. O `--root` nunca era o problema; a
resolução do *script* dependia do cwd.

## 2. Correções

### `tools/static_cards.py`

- Novo `_resolve_cli_root(raw_root)`:
  - resolve `--root` uma única vez (`realpath(abspath(...))`);
  - exige diretório existente, falhando com `StaticCardsError("RAIZ_INVALIDA")`
    em vez de criar saídas parciais;
  - `main()` passou a usar esse resolvedor dentro do `try` (erro controlado,
    exit 1).
- Saídas e `static-manifest.json` continuam derivados do valor absoluto
  (`render_local.rel(root, ...)`), sem caminho de máquina no manifesto.

### `tools/tests/test_static_cards.py`

- `SCRIPT = os.path.join(ROOT, "tools", "static_cards.py")` — script sempre
  absoluto.
- `_run_cli(...)` executa o CLI a partir de um `TemporaryDirectory` neutro em
  `<ROOT>/.workspace/tmp` (criado e removido pelo próprio teste), com
  `encoding="utf-8"`. `--root ROOT` é o único vínculo com o checkout.
- `tearDownModule` remove `<ROOT>/.workspace/tmp` quando vazio.
- Os dois testes de CLI (`--tenant/--campaign` e `--all`) usam `_run_cli`.

Resultado: **13/13 OK**. O número é 13 (não 12) porque a suíte já incorporou
o teste de regressão `test_caminhos_os_nativos_e_normpath` do fix anterior de
path longo (commit `d84ffdb`); a cobertura existente foi preservada.

## 3. `publish_pack` — requisitos já integrados, validados nesta rodada

A base `3f8cb1a` já contém a implementação pedida:

- `resolve_workspace_root(root)` via `git rev-parse --git-common-dir`, com
  fallback para `<raiz>/.workspace` (tools/publish_pack.py:116).
- `_resolve_artifact_path` confina o `archivePath` ao workspace principal
  (linha 140); o checklist registra `resolvedFrom`, `presentOnDisk` e
  `sha256_disk_ok`.
- `tools/tests/test_publish_pack.py` roda em `tempfile.TemporaryDirectory`,
  usa `>= 4` tenants / `>= 8` campanhas e prova por snapshot que
  `04-legendas/pacotes-publicacao/` não é tocado pela suíte.

Validação:

```
python -m unittest tools/tests/test_publish_pack.py -v   -> 10/10 OK
python tools/publish_pack.py --all --json                -> exit 0
```

Resultado do `--all`: **10 pacotes / 5 tenants, 0 violações de guardrails,
`autoPublish: false` em todos**.

### Achado de estação (não regravado no repositório)

O `--all` marcou `sha256_disk_ok: false` apenas para
`multitrack-hub/camp-shorts-completo-multitrack-001`: o MP4 local em
`.workspace/archives/` tem 824.561 bytes e hash
`3664629c...`, enquanto o manifesto versionado registra 352.456 bytes e
`5b5d44a0...`. A mídia foi re-renderizada nesta estação; o checklist
versionado reflete a estação de release. Para não persistir estado local de
máquina, o arquivo foi restaurado (`git checkout --`) e a divergência fica
registrada aqui. Nenhuma mudança de código foi necessária.

## 4. Validação final

```
python -m unittest tools/tests/test_static_cards.py tools/tests/test_publish_pack.py
-> Ran 23 tests ... OK
```

- `git status --short -- 04-legendas/pacotes-publicacao/` → vazio (limpo).
- `git status --short` antes do commit: apenas `tools/static_cards.py` e
  `tools/tests/test_static_cards.py` modificados; caches `__pycache__`
  removidos.
- Commit local na branch `codex/etapa5b-agente2`, sem push.

## 5. Arquivos alterados nesta rodada

- `tools/static_cards.py` — `_resolve_cli_root` + uso no `main`.
- `tools/tests/test_static_cards.py` — script absoluto, cwd neutro, `--root`.
- `.workspace/devlogs/etapa5-agente2b.md` — este relatório.