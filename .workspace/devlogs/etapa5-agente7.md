# Devlog — Etapa 5B / Agente 6 (qualidade e documentação técnica)

> **Data:** 2026-11-20  
> **Branch:** `codex/etapa5b-agente6`  
> **Worktree:** `.workspace/worktrees/etapa5b-agente6`  
> **Base:** `main` @ `3f8cb1a`  
> **Escopo:** suíte de contratos de tenants robusta a 4/5 tenants, cobertura do nicho regulado `clinica-vital` e guia de novo nicho

> Nota de nome: o arquivo segue literalmente o caminho `.workspace/devlogs/etapa5-agente7.md` indicado na tarefa, embora esta seja a entrega do Agente 6.

## 1. Objetivo

Atuar como Engenheiro de Qualidade e Documentação Técnica na Etapa 5B, dentro do território exclusivo:
fazer a suíte `tools/tests/test_tenant_contracts.py` passar tanto com 4 tenants quanto após a integração do
5º tenant (`clinica-vital`), cobrir o nicho regulado com contratos em memória e com verificação condicional
no disco, e atualizar `docs/guia-novo-nicho.md` com a referência oficial e o fluxo completo pós-criação.

## 2. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/tests/test_tenant_contracts.py` | evoluído | contagens globais `>= 4`; `test_01` renomeado para `core_tenants` com os quatro tenants originais; `test_07` com `>= 4` e `clinica-vital` condicional; `test_08` reescrito como validação **em memória** (brand-kit + guardrails literais); `test_09` reescrito como validação **condicional no disco** (`Path.exists()` + `skipTest`) cobrindo `load_and_validate_tenant(strict=True)`, fixture e 2 campanhas |
| `docs/guia-novo-nicho.md` | atualizado | `clinica-vital` promovido a **referência oficial** para saúde/estética; novo **Passo 6** com o fluxo pós-criação (`static_cards.py`, `derivative_formats.py`, `publish_pack.py`, `campaign_calendar.py`, `review_dashboard.py`, `release_audit.py`, `devlog_sync.py`); bloco do nicho regulado com o mesmo fluxo completo e nota sobre contagens `>= 4` |
| `.workspace/devlogs/etapa5-agente7.md` | novo | este relatório |

## 3. Decisões de desenho

- **Contagens `>= 4`, nunca `== 5`:** a base desta worktree já contém `clinica-vital` (o commit de release
  `3f8cb1a` registra 5 tenants/10 campanhas), mas a suíte não deve depender disso. `test_01` e `test_07`
  exigem apenas os quatro tenants originais; a presença do 5º é verificada à parte.
- **Contratos clínicos em memória (`test_08`):** os literais de `brand-kit` e `guardrails` são cópias dos
  contratos reais, validados contra os schemas com `validate_brand_kit` / `validate_guardrails_contract`.
  O teste cobre explicitamente o bloqueio de `antes e depois`, `cura garantida`, `diagnostico online`
  (e a variante acentuada) e `lembrete automatico` (e a variante acentuada), elementos de UI proibidos,
  a separação auditável entre `/avaliacao/[clinicId]` (`public-booking`) e `/gestor/consultas`
  (`manager-agenda`) e a política `allowAudioTrack == False` com `-an`, `requireSrt` e narração externa.
  Por não ler `tenants/`, este teste roda inclusive antes do merge do 5º tenant.
- **Disco condicional (`test_09`):** `if not (Path(REPO_ROOT) / "tenants" / "clinica-vital").exists():`
  encerra com `self.skipTest(...)`, que é mais informativo que um `return` silencioso. Quando o diretório
  existe, valida `load_and_validate_tenant("clinica-vital", strict=True)`, a fixture e as duas campanhas
  (tempos, textos contra guardrails, rotas por superfície e caso de booking).
- **Documentação sem inventar CLI:** todas as flags documentadas foram conferidas nos `argparse` das
  ferramentas (`--types` em `static_cards.py`, `--tenant`/`--campaign` em `derivative_formats.py`,
  `--all`/`--tenant`/`--slug` em `publish_pack.py`, `--start-date` em `campaign_calendar.py`,
  `--build`/`--serve` em `review_dashboard.py`).

## 4. Evidências de validação (nesta estação)

```
$ python -m unittest tools/tests/test_tenant_contracts.py -v
Ran 9 tests em ~0,18 s — OK   (PYTHON_EXIT_CODE=0)
  test_01_core_tenants_pass_contract_validation ... ok
  test_02_marca_salao_brand_kit_and_fixture_sync_with_pilot ... ok
  test_03_ns002_artifacts_pass_marca_salao_guardrails ... ok
  test_04_invalid_brand_kit_rejected_by_schema ... ok
  test_05_forbidden_claims_and_ui_elements_blocked_per_tenant ... ok
  test_06_fixture_rejects_generic_or_e2e_placeholders ... ok
  test_07_cli_exit_codes ... ok
  test_08_clinica_vital_regulated_niche_contracts_in_memory ... ok
  test_09_clinica_vital_contracts_and_campaigns_on_disk ... ok

Prova de robustez com 4 tenants (REPO_ROOT apontado para um diretorio temporario
dentro da worktree, com schemas copiados e SEM tenants/clinica-vital):
  IN_MEMORY_WITHOUT_TENANT_DIR=OK
  DISK_TEST_SKIPPED=tenant clinica-vital ainda nao integrado nesta worktree
```

O diretorio temporario dessa prova foi removido ao final; nenhum arquivo de `tenants/` foi criado,
renomeado ou apagado.

## 5. Limitações

- A simulacao de 4 tenants foi feita por substituicao de `REPO_ROOT` em processo isolado, nao por
  remocao do diretorio real (fora do territorio autorizado). Os testes `test_01` e `test_07` foram
  inspecionados e nao exigem `clinica-vital`.
- `test_08` replica os contratos clinicos como literais; se o tenant real mudar, o `test_09` (disco)
  continua sendo a fonte de verdade. A duplicacao e intencional para manter o teste em memoria independente.
- Nao executei render, derivados, cards, pacotes, calendario, portal ou release gate: a tarefa e de
  qualidade/documentacao e os comandos do Passo 6 foram validados apenas quanto as flags.

## 6. Arquivos nao tocados

`contexto_projeto.md` nao foi editado. Nenhum arquivo foi criado em `tenants/`. Nenhuma worktree de outro
agente foi acessada. Nenhum post, campanha, calendario ou portal foi publicado ou alterado.

## 7. Handoff

- Branch pronta para merge: `codex/etapa5b-agente6`.
- Comando de verificacao rapida: `python -m unittest tools/tests/test_tenant_contracts.py -v`.
- Ao integrar, nao ha contagens fixas a ajustar nesta suite (`>= 4` ja cobre 4 e 5 tenants); a
  consolidacao de `tools/tests/test_factory_cli.py` continua sendo responsabilidade do integrador.
