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