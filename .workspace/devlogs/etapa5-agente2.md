# Etapa 5B — Agente 2 — Handoff pós-aprovação e correção do publish_pack

**Data:** 2026-11-20
**Papel:** Engenheiro Sênior de Distribuição & Automação Editorial (Agente 2 de 4, paralelo)
**Branch:** `codex/etapa5b-agente2-handoff-aprovacoes`
**Worktree:** `.workspace/worktrees/etapa5b-agente2` (a partir de `main` = `edd56e8`)
**Raiz da estação:** `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`

> Observação de ambiente: o primeiro `git worktree add` falhou em
> `platform/examples/...` por limite de caminho do Windows (MAX_PATH). O
> comando foi repetido com `git -c core.longpaths=true worktree add ...`, sem
> alterar configuração global nem do repositório. Nenhuma worktree de outro
> agente foi tocada.

---

## 1. Correção definitiva de `tools/publish_pack.py`

### Problema

O checklist calculava `sha256_disk_ok` da mídia abrindo o caminho relativo da
entrega. Os MP4s não são versionados: em qualquer worktree o arquivo não
existe ali, e a auditoria de vídeo caía sempre em `false`.

### Mudança

- `resolve_workspace_root(root)` implementado com o padrão de
  `derivative_formats.py` / `review_dashboard.py`: prefere
  `<raiz>/.workspace/archives`; em worktree resolve o checkout principal via
  `git rev-parse --git-common-dir` e usa o `.workspace/` de lá. Raiz sem
  checkout git cai no próprio `<raiz>/.workspace`.
- `_main_checkout_root(root)` isola a chamada git (timeout de 15s, falha
  silenciosa → fallback).
- `_resolve_artifact_path(root, workspace_root, entry)` resolve
  `archivePath` (`.workspace/archives/...`) contra o workspace principal e
  confina o resultado (`render_local.contained`). Artefatos versionados (SRT,
  narração, storyboard) continuam relativos à raiz do checkout.
- `_build_checklist(...)` passou a receber `root_real` + `workspace_root`, em
  vez de inferir três níveis acima do pacote. Cada item de mídia agora traz
  `archivePath`, `resolvedFrom` (`archive`/`delivery`/`fora_da_raiz`),
  `presentOnDisk` e `sha256_disk_ok`. `guardrailStatus` sempre inclui
  `srt_violations` e `narration_violations` (lista vazia quando ok).

### Execução obrigatória

```
python tools/publish_pack.py --all --json
```

Resultado: **8 pacotes / 4 tenants**, **0 violações de guardrails**,
`autoPublish: false` em todos. Os 8 `checklist-publicacao.json` foram
regravados com os campos novos (diff esperado e restrito a
`04-legendas/pacotes-publicacao/**`).

---

## 2. Testes de `tools/publish_pack.py` refatorados

`tools/tests/test_publish_pack.py` não usa mais a raiz do repositório para
escrever: `setUpClass` monta uma raiz em `tempfile.TemporaryDirectory` com
cópia de `tenants/`, `schemas/`, das entregas (manifest.json, `.srt`,
`_narracao.txt`) e de `.workspace/archives/` sintéticos com hash coerente com
o manifesto. Contagens são dinâmicas (`>= 4` tenants, `>= 8` campanhas).

Casos (10): geração por tenant, hashes dos arquivos gravados, UTM por canal,
CTA de Instagram, bloqueio de `forbiddenClaims`, `_audit` abortando,
integridade do checklist, `resolve_workspace_root` (raiz temporária, raiz
falsa e raiz real com archives), hash do vídeo conferido em `archives/` e
snapshot provando que `04-legendas/pacotes-publicacao/` versionado não é
alterado pela suíte.

---

## 3. `tools/handoff_bundler.py` (novo)

CLI:

```
python tools/handoff_bundler.py [--approvals-file <json>]
    [--date YYYY-MM-DD | --all-approved] [--include-pending]
    [--output-dir .workspace/handoff-diario] [--root <raiz>] [--json]
```

API: `build_handoff_bundle(root=..., approvals_file=None, date=None,
all_approved=False, include_pending=False, output_dir=None)`.

### Entradas

- Aprovações do titular: default `<workspace>/tmp/aprovacoes-titular.json`
  (workspace resolvido, inclusive o do checkout principal a partir de
  worktree). Schema **v1** (`aprovada: true`) e **v2**
  (`decisao: "aprovado"`) normalizados por `_decision`.
- `04-legendas/calendario-editorial.json` (slots).
- Pacotes sociais (`04-legendas/pacotes-publicacao/<tenant>/<slug>/`) e
  `derivatives.json` das entregas.

### Travas de segurança

- Sem `--include-pending`, só campanhas **explicitamente aprovadas** entram.
  Sem nenhuma aprovada, retorna exatamente:
  `{"ok": true, "bundledSlots": 0, "reason": "NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR"}`.
- Decisão `ajuste` nunca entra, nem com `--include-pending` (registrada em
  `skipped` como `AJUSTE_SOLICITADO`).
- `autoPublish` é sempre `false` (manifesto, índice e JSON de retorno).
- Todo caminho é resolvido e confinado (raiz do projeto para saída e
  pacotes; workspace resolvido para aprovacoes e archives). Nomes de slot,
  tenant, campanha e canal passam por regex estrita.
- A copy final (após substituição da URL UTM do slot) é reauditada com
  `tenant_validator.validate_text_against_guardrails`; violação aborta o slot.
- Mídia copiada é verificada por SHA-256; hash divergente remove o arquivo e
  marca `mediaCopied: false` + `error: HASH_DIVERGENTE` (nunca entrega mídia
  inconsistente).

### Saída por slot

`.workspace/handoff-diario/<dataSugerida>/<slotId>-<tenantId>-<canal>/`:

- `POSTAGEM-MANUAL.md` — status de aprovação/selo `PREVIA_NAO_APROVADA`,
  data e janela BRT, conta/marca, canal, formato (`9:16` / `1:1` / `16:9`),
  mídia esperada e disponibilidade local, `autoPublish: false`, alerta
  explícito de locução externa em tenants `-an`, copy pronta, URL UTM
  completa e checklist numerado de 5 passos.
- `copy-pronta.txt` — copy do canal com a URL UTM do slot (na Onda 2 troca
  `utm_content` para `repurpose-1x1` / `repurpose-16x9`).
- `handoff-manifest.json` — metadados, `approvalStatus`, `audioPolicy`,
  `sha256Expected`/`sha256Copied`/`hashVerified`, `mediaCopied`, bloco de
  `cover`, `guardrailsAudited` e `autoPublish: false`.
- `<slug>.mp4` (Onda 1), `<slug>-1x1.mp4` ou `<slug>-16x9.mp4` (Onda 2) e
  `cover.png`, copiados de `<workspace>/archives/` quando existem.

Índice consolidado em `.workspace/handoff-diario/INDICE-OPERACIONAL.md` e
`indice-operacional.json` (tabela por data/slot/canal, status e mídia local).

### Comportamento nesta estação

`.workspace/archives/` está vazia nesta estação (só `test-deriv-ms`). Com as
aprovações reais ausentes, a execução padrão devolve o JSON limpo de "nenhuma
campanha aprovada". Em smoke test com aprovações sintéticas, os 4 slots da
campanha `marca-salao/camp-saas-demo-marca-salao-001` foram empacotados com
`mediaCopied: false` e `error: MIDIA_AUSENTE_NESTA_ESTACAO`, que é o
diagnóstico correto — o handoff continua utilizável e a ficha aponta a
estação onde copiar o MP4.

---

## 4. Suíte `tools/tests/test_handoff_bundler.py` (12 testes)

Raiz temporária própria com `tenants/`, `schemas/`, calendário de 6 slots
(4 tenants, Ondas 1 e 2), pacotes copiados e `.workspace/archives/` com
mídias sintéticas + hashes atualizados. Casos:

1. Sem aprovações → JSON limpo (`bundledSlots == 0`, reason exata).
2. Schema v1 (`aprovada: true`).
3. Schema v2 (`decisao: "aprovado"`).
4. Filtragem seletiva: apenas a campanha aprovada (3 slots), nada de outro tenant.
5. Roteamento de mídia: 9:16 (`<slug>.mp4`), 1:1 (`-1x1.mp4`), 16:9 (`-16x9.mp4`) + `cover.png`, `mediaCopied`/`hashVerified` verdadeiros.
6. `--include-pending` com selo `PREVIA_NAO_APROVADA` e exclusão de `ajuste`.
7. Filtro `--date` (1 slot) e data sem aprovado (`NENHUM_SLOT_APROVADO_NA_DATA`).
8. Documentos do slot, 5 passos (sem passo 6), URL UTM `repurpose-16x9` na copy, `autoPublish: false`, `manualOnly: true`.
9. Alerta de locução externa só em `-an`; `multitrack-hub` sem alerta e `externalNarrationAlert: false`.
10. Contenção de path: output `../`, aprovacoes `../../` e slotId `../escape` bloqueados.
11. CLI `--json` via subprocess: exit 0 e JSON válido.
12. Índice `INDICE-OPERACIONAL.md` + `indice-operacional.json`.

Comando final:

```
python -m unittest tools/tests/test_publish_pack.py tools/tests/test_handoff_bundler.py -v
```

Resultado: **22 testes, OK** (rodado também com `-W error::ResourceWarning`).

---

## 5. Estado do worktree e limpeza

- Scratch removido: `.workspace/tmp/`, `.workspace/handoff-diario/` (smoke),
  `.workspace/tmp-publish.*`, `tools/__pycache__`, `tools/tests/__pycache__`.
- Alterações permanentes: `tools/publish_pack.py`,
  `tools/tests/test_publish_pack.py`, `tools/handoff_bundler.py`,
  `tools/tests/test_handoff_bundler.py`, os 8 `checklist-publicacao.json` e
  este devlog.
- Nenhum arquivo de `04-legendas/pacotes-publicacao/` foi sujado pela suíte
  (provado por snapshot no teste 10 do publish_pack); a regravação existente
  vem apenas do comando `--all` exigido, com os campos novos do checklist.
- Commit local na branch `codex/etapa5b-agente2-handoff-aprovacoes`; sem push.

## 6. Próximos passos sugeridos para integração

1. Revisar o diff dos 8 checklists (apenas campos novos: `archivePath`,
   `resolvedFrom`, `presentOnDisk`, listas de violações).
2. No merge, manter `resolve_workspace_root` alinhado ao padrão já existente
   em `derivative_formats.py`/`review_dashboard.py`.
3. Quando o titular aprovar campanhas no portal
   (`review_dashboard.py --serve`), rodar
   `python tools/handoff_bundler.py --all-approved --json` na estação que
   possui `.workspace/archives/` para empacotar com mídia.