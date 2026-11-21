# Devlog — Etapa 5B / Agente 4 (orquestrador end-to-end e analytics)

> **Data:** 2026-11-20  
> **Branch:** `codex/etapa5b-agente4-orquestrador-e2e-analytics`  
> **Worktree:** `.workspace/worktrees/etapa5b-agente4`  
> **Base:** `main` @ `edd56e8`  
> **Escopo:** orquestrador unificado, auditor/simulador UTM, playbook de analytics, testes e CI

## 1. Objetivo

Fechar a Etapa 5B no território do Agente 4: transformar o `factory_cli.py` em um
orquestrador mestre determinístico (contratos → render → derivados → cards →
pacotes → calendário → portal → UTM → release gate), entregar a auditoria UTM com
simulação sintética das duas ondas e documentar o mapa de eventos por nicho com
receitas de GA4, Plausible e Umami.

## 2. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/factory_cli.py` | evoluído | subcomando `pipeline` com 9 estágios, imports opcionais, JSON por estágio com `durationMs`, contagens consolidadas |
| `tools/utm_simulator.py` | novo | auditoria de 100% das URLs UTM + simulação determinística de tráfego (`--simulate-traffic`) |
| `tools/tests/test_factory_cli.py` | atualizado | contagens dinâmicas (`>= 4` tenants, `>= 8` campanhas), testes de `pipeline` filtrado e `--all` |
| `tools/tests/test_utm_simulator.py` | novo | 11 testes: domínio, parâmetros, padronização, colisão, derivação, simulação, CLI e contenção de caminho |
| `docs/analytics-utm-playbook.md` | novo | eventos por nicho (5, incluindo `clinica-vital`), receitas GA4/Plausible/Umami, validação e rotina semanal |
| `.github/workflows/local-render-validation.yml` | atualizado | trigger `01-insta-stories/deliveries/**`, 4 novas suites no CI, smoke de `pipeline --all --skip-render` |
| `.workspace/devlogs/etapa5-agente4.md` | novo | este relatório |

## 3. Desenho do `pipeline`

Ordem fixa dos estágios (sempre os 9 no relatório, mesmo quando pulados):

1. `contratos` → `tenant_validator.load_and_validate_tenant(..., strict=True)`.
2. `render` → `preset_runner.run_preset_pipeline`; com `--skip-render`, verifica
   `02-reels-shorts/deliveries/<tenant>/<slug>/manifest.json` e registra o preset
   e `audioStreams` declarados.
3. `derivados` → `derivative_formats.generate_campaign_derivatives` (produção) ou
   verificação de `derivatives.json` + hashes quando o arquivo existe no disco.
4. `cards-estaticos` → `static_cards.generate_campaign_static_cards` ou verificação
   de `01-insta-stories/deliveries/<tenant>/<slug>/static-manifest.json`.
5. `pacotes` → `publish_pack.generate_pack` ou verificação de
   `checklist-publicacao.json` + 3 legendas, exigindo `autoPublish=false` e
   `guardrailsAudited=true`.
6. `calendario` (só `--all`) → `campaign_calendar.build_editorial_calendar` em
   memória, usando `--start-date`/`--weeks` ou os valores do calendário versionado.
7. `portal` (só `--all`) → `review_dashboard.build_portal` (produção) ou
   verificação de `05-review-portal/`.
8. `utm` → `utm_simulator.audit_and_simulate_utm`.
9. `release-gate` → `release_audit.run_release_audit(root, strict=args.strict_audit)`.

Decisões:

- **Importação opcional real:** módulos das etapas paralelas são importados via
  `importlib`; se ausentes, o estágio vira `skipped` com motivo e o pipeline segue.
  O Release Gate é fail-closed: ausência do módulo reprova.
- **`--skip-render` é modo de verificação**, não de omissão: todo artefato versionado
  é conferido (manifesto, derivados, cards, pacote, portal). Hashes só são exigidos
  quando o binário local existe, alinhado à política do `release_audit` para mídia
  não rastreada.
- **Compatibilidade total:** `list` e `render` mantêm assinatura, saída e exit codes.
- **Falha por estágio:** `StageFailure` preserva detalhes estruturados (ex.: domínios
  do release gate, códigos UTM) mesmo quando o estágio reprova.

## 4. Auditoria e simulação UTM

- Fonte primária: `04-legendas/calendario-editorial.json` (32 slots, 4 tenants).
- URL derivada para campanha ainda não agendada: `https://<domain>/?utm_source=
  <utmDefaults.utm_source>&utm_medium=<utmDefaults.utm_medium>&utm_campaign=<slug>
  &utm_content=<tenantId>`, marcada com `origin=derived`.
- Regras de erro: HTTPS, domínio do brand-kit, 4 parâmetros obrigatórios, alfabeto
  `[a-z0-9._-]`, `utm_campaign == slug`, ausência de duplicidade e de colisão entre
  tenants (campanha isolada e par campanha+conteúdo).
- Simulação: RNG semeado por `sha256(seed + slug + canal + midia + url)`; cobre
  Reels, Shorts, Feed 1:1 (`repurpose-1x1`) e Vídeo 16:9 (`repurpose-16x9`).
  Saída em `utm_sessions_sample.json` + `utm_attribution_summary.md`.
  `financialSimulation: false` e `revenueBRL: null` em 100% das sessões.
- Catálogo de eventos por nicho inclui `clinica-vital` (nicho em onboarding), mesmo
  sem tenant ativo, sem gerar URL antes de existir brand-kit.

## 5. Evidências de validação (nesta estação)

```
$ python tools/factory_cli.py pipeline --tenant marca-salao \
    --campaign camp-saas-demo-marca-salao-001 --skip-render --json
ok=True (287–405 ms)
estágios: contratos ok, render ok, derivados ok, cards-estaticos ok, pacotes ok,
          calendario skipped, portal skipped, utm ok, release-gate ok
counts: 1 tenant, 1 campanha, 7 cards, 32 URLs UTM, 7/7 domínios ok

$ python tools/factory_cli.py pipeline --all --skip-render --json
ok=True (~1,1 s)
counts: 4 tenants, 8 campanhas, 8 entregas, 8 derivados, 56 cards, 8 pacotes,
        32 slots de calendário, 8 campanhas no portal, 32 URLs UTM, 7/7 domínios ok

$ python tools/utm_simulator.py --json
ok=True, 32/32 URLs, 0 derivadas, 0 erros, 0 avisos

$ python tools/utm_simulator.py --simulate-traffic --out-dir .workspace/tmp/utm-sim --json
472 sessões, 52 conversões, ondas 400/72, pegadas instagram/reels,
youtube/shorts, instagram/feed, youtube/video, facebook/reels

$ python -m unittest tools.tests.test_utm_simulator -v
Ran 11 tests — OK

$ python -m unittest (test_factory_cli 01,03,04,05,06)
Ran 5 tests — OK

$ python tools/release_audit.py --strict --json
7/7 domínios ok, 0 erros, 0 avisos
```

## 6. Limitações desta estação

- `ffmpeg`/`ffprobe` continuam ausentes nesta máquina; por isso o modo de produção
  real (sem `--skip-render`) e a geração de derivados não foram executados aqui.
  O caminho de produção é exercitado no CI, que instala FFmpeg via ação oficial.
- Os testes `test_bootstrap_ffmpeg.py` e `test_handoff_bundler.py` ainda não existem
  nesta branch: pertencem aos Agentes 1 e 2. Foram adicionados à suíte do workflow
  conforme o contrato de integração; a execução completa ocorre na branch integrada.
- Divergência intencional entre ramos: estágios de módulos paralelos ficam `skipped`
  até que os arquivos correspondentes estejam presentes na branch final.

## 7. Arquivos não tocados

`contexto_projeto.md` não foi editado, conforme território exclusivo. Nenhuma
worktree de outro agente foi acessada. Nenhum post, tenant, campanha, calendário ou
portal foi publicado/alterado.

## 8. Handoff

- Branch pronta para merge: `codex/etapa5b-agente4-orquestrador-e2e-analytics`.
- Comando de verificação rápida: `python tools/factory_cli.py pipeline --all
  --skip-render --json`.
- Próximo agente/integrador: rodar a suíte completa no CI, onde FFmpeg está
  disponível, e confirmar `pipeline --all` no modo de produção após o merge dos
  Agentes 1–3.

---

# Revisão de operações editoriais — handoff bundler (Agente 3 de 8)

> **Data:** 2026-11-20
> **Branch:** `codex/etapa5b-agente3` (worktree `.workspace/worktrees/etapa5b-agente3`)
> **Base:** `main` @ `3f8cb1a` (Etapa 5B consolidada)
> **Escopo:** validar/entregar `tools/handoff_bundler.py` + suíte, corrigir conformidade de armazenamento e registrar evidências

> Esta seção foi **anexada** ao relatório anterior do orquestrador (Agente 4),
> preservando integralmente o conteúdo existente.

## 1. Descoberta de estado

A worktree `etapa5b-agente3` já existia na branch `codex/etapa5b-agente3`,
apontando para `main` @ `3f8cb1a`. A `main` avançou de `edd56e8` para `3f8cb1a`
e já integrou o bundler no commit `d10f7c9` (rotulado "Agente 2"). Portanto o
trabalho não foi duplicado: o motor existente foi auditado linha a linha contra
a especificação, e apenas lacunas reais foram corrigidas.

## 2. Auditoria contra a especificação

| Requisito | Estado | Evidência |
| --- | --- | --- |
| CLI com `--approvals-file`, `--date`, `--all-approved`, `--include-pending`, `--output-dir`, `--json` | OK | `main()` em `tools/handoff_bundler.py` |
| API `build_handoff_bundle(...)` | OK | assinatura pública no mesmo módulo |
| 100% stdlib | OK | imports: argparse, hashlib, json, os, re, shutil, sys |
| Schema v1 (`aprovada: true`) e v2 (`decisao: "aprovado"`) | OK | `_decision()` + testes 02/03 |
| Trava sem aprovação → JSON exato com `NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR` | OK | teste 01 |
| `autoPublish` sempre `false` | OK | manifesto, resultado e índice |
| `POSTAGEM-MANUAL.md`, `copy-pronta.txt`, `handoff-manifest.json`, mídia, `cover.png` | OK | teste 08 e e2e |
| Mídia resolvida via `git-common-dir` | OK | `publish_pack.resolve_workspace_root` |
| `INDICE-OPERACIONAL.md` + `indice-operacional.json` | OK | teste 12 |
| Selo `PREVIA_NAO_APROVADA` com `--include-pending` | OK | teste 06 |
| Alerta de locução externa apenas para `-an` | OK | teste 09 (`multitrack-hub` sem alerta) |

## 3. Correção aplicada

- `tools/tests/test_handoff_bundler.py`: o fixture usava
  `tempfile.TemporaryDirectory` (diretório do sistema, fora de `<RAIZ>`),
  violando a regra de armazenamento obrigatório. Passou a usar
  `<RAIZ>/.workspace/tmp/test_handoff_bundler`, removido em `tearDownClass`;
  o import de `tempfile` foi eliminado e o restante da suíte não mudou.

Nenhuma alteração foi feita em `tools/handoff_bundler.py` (já conforme),
`04-legendas/calendario-editorial.*` ou `contexto_projeto.md`.

## 4. Evidências de validação

```bash
python -m unittest tools/tests/test_handoff_bundler.py -v
# Ran 12 tests in 2.384s — OK
```

Cobertura: trava humana (01), schemas v1/v2 (02/03), filtragem seletiva (04),
Onda 1 × Onda 2 com derivados e cover (05), `--include-pending` + exclusão de
`ajuste` (06), `--date` (07), documentos e checklist de 5 passos (08), alerta
`-an` vs AAC (09), contenção de path (10), CLI `--json` exit 0 (11), índice
consolidado (12).

Smoke real (calendário e pacotes versionados + `.workspace/archives`), com
aprovação sintética em `.workspace/tmp` e `--date 2026-11-23`:

- `bundledSlots: 2`, `autoPublish: false`, índice gerado.
- `marca-salao` (`-an`): `mediaCopied: true`, `hashVerified: true`, alerta de
  locução externa presente.
- `multitrack-hub`: `mediaCopied: false`, `error: HASH_DIVERGENTE`
  (arquivo em `archives` com 824.561 bytes; manifesto registra 352.456).
  Comportamento fail-closed correto — a cópia foi descartada. Operacionalmente,
  esse slot exige nova renderização/atualização do manifesto antes do handoff.
- `cover.png` copiado nos dois slots; temporários removidos após o teste.

## 5. Handoff

- Raiz usada: `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`.
- Worktree preservada (já existente, não recriada); nenhuma outra worktree tocada.
- Fixtures de teste e saída smoke ficaram apenas em `.workspace/tmp` (ignorado)
  e foram removidos; nenhum artefato permanente fora do Git.
- Pendência operacional fora do território: reconciliar mídia/manifesto do
  `camp-shorts-completo-multitrack-001` (hash divergente nesta estação).