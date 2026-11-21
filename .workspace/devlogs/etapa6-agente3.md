# Etapa 6 — Agente 3: CLI de aprovações e handoff no orquestrador

> **Data:** 2026-11-20
> **Branch:** `codex/etapa6-agente3`
> **Worktree:** `.workspace/worktrees/etapa6-agente3` (já existente, base `main` @ `8a1b361`)
> **Escopo:** `tools/approval_cli.py`, subcomando `handoff` em `tools/factory_cli.py`, suítes e este relatório

## 1. Objetivo

Dar ao titular uma via auditável fora do navegador para consultar e registrar
decisões editoriais (`aprovado`, `aguardando`, `ajuste`, conferência de locução
externa `-an`) e disparar o empacotamento diário de postagem manual direto pelo
orquestrador mestre, mantendo `autoPublish: false` em todas as operações.

## 2. Isolamento e estado encontrado

- Worktree `etapa6-agente3` já existia na branch `codex/etapa6-agente3`, em
  `main` @ `8a1b361` (Etapa 5B consolidada). Nada foi recriado nem realocado.
- Havia (e permanece) uma modificação não relacionada em
  `platform/examples/execution-packages/...execution-package.json`, fora do
  território deste agente; não foi commitada, revertida ou tocada.
- Nenhuma outra worktree (`etapa6-agente1/2/4..8`) foi acessada.

## 3. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/approval_cli.py` | novo | CLI/API `status`, `decide`, `validate` (stdlib), schema v2, hashes, stale, escrita atômica |
| `tools/factory_cli.py` | evoluído | subcomando `handoff`; `list`, `render` e `pipeline` intactos |
| `tools/tests/test_approval_cli.py` | novo | 14 testes |
| `tools/tests/test_factory_cli.py` | atualizado | `test_07` (0 aprovadas) e `test_08` (aprovação real em tmp) |
| `.workspace/devlogs/etapa6-agente3.md` | novo | este relatório |

## 4. Desenho do `approval_cli`

- **Workspace:** `resolve_workspace_dir` delega a
  `review_dashboard.resolve_workspace_dir` (mesmo `git rev-parse --git-common-dir`),
  então o store é `<workspace>/tmp/aprovacoes-titular.json` em qualquer worktree.
- **Descoberta:** varre `tenants/*/campaigns/*.json` (10 campanhas hoje) e cruza
  por `(tenantId, slug)`.
- **Decisões:** `aprovado | aguardando | ajuste`; `ajuste` exige `--notes`
  não vazio; `--reviewer` é obrigatório; item desconhecido é recusado.
- **Hashes:** lê `02-reels-shorts/deliveries/<tenant>/<slug>/manifest.json` e
  grava `video`, `srt`, `narracao`, `storyboard` (mesmas chaves do portal).
- **`updatedAt`:** ISO-8601 UTC por campanha, aditivo ao contrato v2.
- **Escrita atômica:** arquivo temporário na mesma pasta + `os.replace`; o
  temporário é removido em qualquer saída.
- **Contenção:** `--approvals-file` precisa resolver dentro da raiz do checkout
  ou do workspace resolvido (`APPROVALS_FORA_DA_RAIZ`).
- **Segurança:** nenhuma operação publica ou agenda; `autoPublish` é sempre
  `false` nas respostas e o documento não contém esse campo.

### Compatibilidade de schema (nuance registrada)

O `POST /api/approvals` do portal valida estritamente um conjunto de chaves que
**não inclui `updatedAt`**. O `GET` não valida. Portanto:

- o arquivo gerado pela CLI é lido e exibido pelo portal normalmente;
- uma reexportação pelo navegador descarta `updatedAt` (sem corromper os demais
  campos), e a CLI continua operando (o campo é opcional na leitura).

`tools/review_dashboard.py` não foi alterado (fora do território).

## 5. Contratos JSON (exemplos reais)

`python tools/approval_cli.py status --json` (sem store):

```json
{
  "ok": true,
  "autoPublish": false,
  "exists": false,
  "approvalsFile": ".workspace/tmp/aprovacoes-titular.json",
  "summary": {"total": 10, "aprovadas": 0, "aguardando": 10, "ajuste": 0},
  "externalAudioTenants": ["clinica-vital", "estudio-flow", "marca-salao", "meu-salao"],
  "locucaoExternaPendente": [],
  "campaigns": [
    {"tenantId": "clinica-vital", "slug": "camp-saas-demo-clinica-vital-001",
     "decision": "aguardando", "externalAudio": true,
     "locucaoExternaConferida": false, "updatedAt": null}
  ]
}
```

`decide` (trecho da resposta e do arquivo):

```json
{
  "ok": true, "autoPublish": false,
  "tenantId": "marca-salao", "slug": "camp-saas-demo-ns001-agenda-001",
  "decision": "aprovado", "reviewer": "Titular", "updatedAt": "2026-11-21T01:21:43Z",
  "campaign": {
    "tenantId": "marca-salao", "slug": "camp-saas-demo-ns001-agenda-001",
    "campaignId": "SAAS-DEMO-NS001-AGENDA-001", "preset": "saas-demo",
    "politicaAudio": "-an", "decisao": "aprovado",
    "locucaoExternaConferida": true, "observacoes": "",
    "hashes": {"video": "...", "srt": "...", "narracao": "...", "storyboard": "..."},
    "updatedAt": "2026-11-21T01:21:43Z"
  }
}
```

Documento gravado: `schemaVersion: 2`, `arquivo: "aprovacoes-titular.json"`,
`origem: "tools/approval_cli.py"`, `exportadoEm`, `revisor`, `resumo`
(`totalCampanhas/aprovadas/ajustes/pendentes`) e `campanhas` ordenadas.

`validate`:

```json
{
  "ok": true, "exists": true, "total": 1,
  "summary": {"total": 1, "aprovadas": 1, "aguardando": 0, "ajuste": 0},
  "errors": [], "warnings": [], "staleApprovals": [],
  "campaigns": [{"tenantId": "marca-salao", "slug": "camp-saas-demo-ns001-agenda-001",
                 "decision": "aprovado", "staleApproval": false, "changedHashes": [],
                 "hashCheck": "ok"}]
}
```

`staleApproval`: quando o `manifest.json` muda após a decisão, a campanha sai
com `staleApproval: true` e `changedHashes` (ex.: `["video"]`), `ok: false`.
Sem manifesto, `hashCheck: "sem_hashes"` e sem falso positivo. Aviso (não erro):
`-an` aprovado sem `--external-audio-checked`.

## 6. Subcomando `handoff` no orquestrador

```bash
python tools/factory_cli.py handoff --date 2026-11-23 \
  --approvals-file .workspace/tmp/aprovacoes-titular.json \
  --output-dir .workspace/handoff-diario --json
```

Fluxo: importa `approval_cli` e `handoff_bundler` via `_optional_module`
(mesmo padrão dos módulos paralelos), roda `cmd_validate`, aborta com
`APROVACOES_INVALIDAS` somente em erros de schema/campanha e chama
`build_handoff_bundle`. Saída unificada:

```json
{
  "schemaVersion": 1, "ok": true, "autoPublish": false,
  "mode": "date", "date": "2026-11-23",
  "approvalAudit": {"ok": true, "exists": true, "total": 1,
                    "summary": {"total": 1, "aprovadas": 1, "aguardando": 0, "ajuste": 0},
                    "staleApprovals": [], "warnings": []},
  "handoff": {"ok": true, "autoPublish": false, "bundledSlots": 1,
              "dates": ["2026-11-23"], "reason": null, "slots": ["..."]}
}
```

Stale não bloqueia o bundle (o bundler já falha fechado por hash na mídia);
o relatório expõe `staleApprovals` para decisão humana. `list`, `render` e
`pipeline` mantêm assinatura, saída e exit codes.

## 7. Testes

```bash
python -m unittest tools/tests/test_approval_cli.py tools/tests/test_factory_cli.py tools/tests/test_handoff_bundler.py -v
# Ran 34 tests — OK (skipped=1)
```

- `test_approval_cli.py` — 14/14: status sem store; decide aprovado/ajuste/
  aguardando; notes obrigatórias em ajuste; hashes do manifesto; `staleApproval`;
  validate reprovando schema/campanha; roundtrip `handoff_bundler.load_approvals`;
  contenção de path; CLI `--json`; escrita atômica sem `.tmp`; migração v1.
- `test_factory_cli.py` — 8 testes: os 6 anteriores + `handoff` com 0 aprovadas
  (JSON limpo e `NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR`) e com campanha
  aprovada em diretório temporário (`bundledSlots >= 1`, `autoPublish: false`).
  `test_02` (render binário) segue `skipped` porque `ffmpeg` não está no PATH
  desta estação.
- `test_handoff_bundler.py` — 12/12, sem regressão.

## 8. Smoke real (dados de produção fictícios versionados)

Sequência executada no checkout com store descartável em
`.workspace/tmp/etapa6-agente3-smoke/` (removido ao final):

```
decide  -> ok, aprovado, 2026-11-21T01:21:43Z, hashes: narracao/srt/storyboard/video
validate -> ok, total 1, stale [], errors [], warnings []
factory handoff --date 2026-11-23
  -> ok, autoPublish false, audit.aprovadas 1, bundled 1 (slot-001 marca-salao)
  -> mediaCopied true, POSTAGEM-MANUAL.md + copy-pronta.txt + cover.png + handoff-manifest.json
```

Nenhum store permanente foi criado; o arquivo padrão
`<workspace>/tmp/aprovacoes-titular.json` do checkout principal não foi tocado.

## 9. Limites e pendências para a consolidação

1. `review_dashboard.py` não foi alterado; se o time quiser preservar
   `updatedAt` numa reexportação pelo navegador, o conjunto de chaves do POST
   precisa ser estendido pelo dono desse arquivo.
2. `test_factory_cli.test_02` continua dependente de `ffmpeg`; o CI cobre.
3. Stale apenas detecta mudança de hash declarado no manifesto; divergência
   entre arquivo arquivado e manifesto continua sendo bloqueada pelo
   `handoff_bundler` (fail-closed por hash na cópia).

## 10. Handoff de armazenamento

- Raiz usada: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.
- Worktree: `.workspace/worktrees/etapa6-agente3` (existente, preservada).
- Fixtures de teste e smoke: somente em `.workspace/tmp` (ignorado), removidos.
- Ferramentas portáteis: nenhuma.
- Arquivos permanentes do commit: `tools/approval_cli.py`,
  `tools/tests/test_approval_cli.py`, `tools/factory_cli.py`,
  `tools/tests/test_factory_cli.py` e este devlog.
- Nenhum arquivo ou diretório relacionado ao projeto foi criado ou mantido
  fora de `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.