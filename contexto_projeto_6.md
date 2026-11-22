# Contexto do projeto — consolidação v6 (pós-Etapa 13 + Ajuste Fino 13.1)

> **Classificação (22/11/2026): snapshot histórico.** Este documento descreve a base
> `642f570` / branch `feat/etapa-13-1-smoke-tests-and-context-v6` (Etapa 13.1), com medições
> reais daquela entrega. Ele **não** descreve a base atual: a Etapa 14 acrescentou
> `test_tenant_scaffolder` ao `fast` (29 módulos / smoke 25 / all 51) e entregou
> `tenant_scaffolder.py`, `--simulate-capacity` e `capacityStatus` — itens que o §7 daqui
> lista como "não implementadas". Para o estado vigente, consulte
> [docs/contexto/ESTADO-ATUAL.md](docs/contexto/ESTADO-ATUAL.md) e
> [docs/README.md](docs/README.md). Números e resultados abaixo permanecem como registro
> daquela base; não foram reexecutados nem alterados retroativamente.

Referência técnica definitiva da fábrica de campanhas multi-tenant até esta entrega.
Documento gerado a partir do código e de execuções reais nesta estação, não de
handoffs anteriores. Onde um número não foi medido nesta execução, está marcado
como tal em vez de estimado.

- **Branch de integração:** `main`
- **Commit base desta consolidação:** `642f570` — `feat(etapa-13): runner de testes isolado, auto-reparo de midia e relatorio executivo por tenant`
- **Branch deste ajuste:** `feat/etapa-13-1-smoke-tests-and-context-v6`
- **Raiz do checkout:** o valor de `git rev-parse --show-toplevel` da estação (`<RAIZ>`); o documento não fixa caminho de máquina
- **Estação de medição:** Windows 10.0.26200, Python 3 stdlib, FFmpeg/FFprobe 9.1-essentials portáteis em `<RAIZ>/.workspace/tools/ffmpeg/`

---

## 1. Resumo executivo e estado da base

A fábrica produz campanhas de vídeo vertical para 5 marcas independentes a partir
de configuração declarativa, com render determinístico por estação, auditoria
editorial transversal, inteligência A/B estatística, empacotamento bit-determinístico
e fechamento de loop pós-publicação. **Nenhuma etapa publica, agenda ou cria
rascunho**: a publicação é sempre manual, por decisão do titular.

### 1.1 Portfólio ativo

| Tenant | Marca | Campanhas | Preset padrão | Política de áudio |
| --- | --- | --- | --- | --- |
| `clinica-vital` | Clínica Vital | 3 | `saas-demo` | `-an` (sem faixa) |
| `estudio-flow` | Estúdio Flow | 2 | `saas-demo` | `-an` (sem faixa) |
| `marca-salao` | Marca Salão | 2 | `saas-demo` | `-an` (sem faixa) |
| `meu-salao` | Meu Salão | 3 | `saas-demo` | `-an` (sem faixa) |
| `multitrack-hub` | Multitrack Hub | 4 | `shorts-completo` | `AAC` (1 faixa, 44100 Hz, stereo) |
| **Total** | **5 tenants** | **14 campanhas** | — | **10 `-an` / 4 `AAC`** |

### 1.2 Calendário editorial

- **7 semanas / 56 slots**, 14 campanhas, 5 tenants.
- Período: `2026-11-23` a `2027-01-05`.
- Onda 1 = 4 semanas (9:16), Onda 2 = 3 semanas (alternância 1:1 / 16:9).
- `statusEditorial: "aguardando_aprovacao_titular"`, `autoPublish: false`.
- **Restrição estrutural:** com 14 campanhas, `onda1 = ceil(14/4) = 4` e
  `onda2 = ceil(14/6) = 3`; o mínimo é **7 semanas**. Chamar
  `build_editorial_calendar(..., weeks=4)` levanta `SEMANAS_INSUFICIENTES`.
- Fonte canônica: `04-legendas/calendario-editorial.json` (+ `.md` e
  `matriz-utm-consolidada.csv`).

### 1.3 Mídia local

84 arquivos de mídia declarados em `.workspace/archives/` (14 masters 9:16 +
70 derivados: 14 × {1:1, 16:9, cover, thumb-16x9, preview-formats}). Todos os
84 verificados por SHA-256 nesta execução, 0 divergentes. Mídia **não é
versionada** (`*.mp4` no `.gitignore`); o que se versiona é o manifesto com
SHA-256, bytes, ffprobe e o comando reproduzível.

---

## 2. Invariantes arquiteturais inegociáveis

1. **100% biblioteca padrão Python.** Nenhuma dependência externa em
   `requirements.txt` / `pyproject.toml`. Módulos usados: `unittest`, `argparse`,
   `json`, `pathlib`, `hashlib`, `shutil`, `tempfile`, `datetime`, `subprocess`,
   `math`, `statistics`, `zipfile`, `re`, `os`, `sys`, `time`, `contextlib`,
   `io`, `inspect`, `http.server`, `threading`.
2. **`autoPublish: false` em toda a cadeia.** Verificado recursivamente pelo gate
   de higiene Git em todos os JSONs versionados. Nenhuma ferramenta publica,
   agenda, cria rascunho ou altera datas de calendário, canais e UTMs.
3. **Isolamento multi-tenant estrito.** Métricas, relatórios, benchmarks e
   reparos são escopados por `tenant_id`. Comparações acontecem **dentro** do
   tenant, nunca entre nichos.
4. **Contenção de caminhos.** Todo acesso a disco passa por
   `render_local.fs_path` (caminhos longos no Windows), `render_local.contained`
   (recusa saída da raiz) e `render_local.write_text_lf` (LF puro, hashes
   estáveis entre Windows e Linux). `workspace_doctor` usa helpers equivalentes
   próprios (`_fs_path`, `_contained`).
5. **Compatibilidade com git worktree.** `review_dashboard.resolve_workspace_dir(root)`
   resolve o `.workspace/` do **checkout principal** via
   `git rev-parse --git-common-dir`, para que worktrees compartilhem a mesma
   mídia e o mesmo store de aprovações.
6. **Higiene de `.workspace/` no Git.** Artefatos locais nunca são rastreados.
   A regra vive em `<RAIZ>/.git/info/exclude` (local por estação), **não** no
   `.gitignore` versionado. `devlogs/` é exceção intencional: permanece
   versionado para consolidação via `devlog_sync`.
7. **Portabilidade estrutural.** Tudo sob `<RAIZ>`; auxiliares em
   `<RAIZ>/.workspace/`. Nenhum artefato em `%TEMP%`, `/tmp` ou pasta de usuário.
   Alinhamento entre estações exclusivamente por Git.
8. **Vídeo sem áudio para tenants `-an`.** Legendas queimadas e sincronizadas,
   SRT e narração TXT separados; o áudio é gerado fora do editor, pelo titular.

---

## 3. Inventário das ferramentas (`tools/`)

65 módulos Python em `tools/`. Núcleo operacional da fábrica:

| Módulo | Papel técnico | Entrada principal |
| --- | --- | --- |
| `tenant_validator.py` | Valida contratos de tenant (brand-kit, guardrails, política de áudio, `uiLabels`). Fonte da lista de tenants. | `list_tenants(root)` · `load_and_validate_tenant(tid, root, strict)` · CLI `--all --json` |
| `preset_runner.py` | **Motor canônico de render do master 9:16.** Desenha cenas em PNG (stdlib), monta comando FFmpeg, queima SRT, valida por ffprobe e grava `manifest.json` + cópia em archives. | `run_preset_pipeline(tenant_id, config_path, output_dir, audio_path=None, root=".", archives_dir=None)` |
| `render_local.py` | Adaptador de render do `CreativeExecutionPackage v1` via ponte Node (`render_bridge.mjs`). Emite `delivery-manifest.json`. **Não** escreve `manifest.json` nem archives. Fornece os wrappers de caminho usados por toda a fábrica. | `run_render(...)` · `fs_path` · `contained` · `write_text_lf` · `ensure_video_tools` · `sha256_file` |
| `derivative_formats.py` | Gera derivados multiformato (1:1, 16:9, cover, thumb-16x9, preview-grid) a partir do master, com auditoria ffprobe e cópia versionada dos PNGs. Grava `derivatives.json` (schema v2), mesclando formatos não solicitados. | `generate_campaign_derivatives(tenant_id, slug, root=".", formats=None, force=False, archives_dir=None)` |
| `editorial_qa.py` | Auditoria editorial transversal em **7 lentes**, com filtro nativo por tenant. `error` reprova sempre; `warning` reprova sob `--strict`. | `run_editorial_qa(root=".", strict=False, tenant=None)` · CLI `--all --strict --json` |
| `utm_report_importer.py` | Importa métricas de analytics, casa com a matriz UTM, roda o comparativo Hook A/B com teste z, detecta fadiga temporal, calcula `tenantBenchmarks` e reconcilia bundles (`bundleAttribution`). | `analyze_performance(...)` · `reconcile_bundles(...)` · CLI `--json` / `--reconcile-bundles` |
| `campaign_calendar.py` | Monta o calendário editorial de 7 semanas, ondas 1/2, janelas BRT, matriz UTM e recomendação de hook por slot. | `build_editorial_calendar(start_date, weeks, root, utm_report, bundle_attribution)` · `discover_campaigns(root)` |
| `approval_cli.py` | Decisões do titular (`aguardando` / `aprovado` / `ajuste`), conferência de locução externa e **promoção assistida de hook** com gate editorial. | `cmd_status` · `cmd_decide` · `cmd_promote_hook(..., dry_run=True, apply_=False)` |
| `publish_bundler.py` | Empacotamento **bit-determinístico** de distribuição: ZIP ordenado, manifesto com SHA-256 por item e do arquivo, gate de aprovação. | `pack_bundle(...)` · `verify_bundle(bundle_path, root)` · CLI `pack` / `verify` |
| `executive_summary.py` | Relatório executivo semanal **por tenant**, somente leitura. Consolida saúde editorial, A/B, fadiga, benchmarks, promoções, bundles e atribuição, com plano de ação recomendatório. | `build_executive_summary(root, tenant_id, week=None, inputs=None)` · CLI `--tenant` / `--all --week --json` |
| `review_dashboard.py` | Portal de revisão humana: `portal-data.json`, `index.html`, `README.md`, servidor local e API de aprovações. Expõe `hookBenchmarks` e `executiveSummary`. | `build_portal(root, output_dir, utm_report, bundle_attribution)` · `resolve_workspace_dir` · `approvals_store_path` |
| `workspace_doctor.py` | Saúde do `.workspace/`: FFmpeg portátil, integridade SHA-256/ffprobe de archives, worktrees, higiene de tmp, snapshot e **auto-reparo cirúrgico**. | `run_workspace_doctor` · `repair_media(root, apply, slug, tenant)` · `audit_manifest_integrity` |
| `release_audit.py` | Auditoria de release em **8 domínios**, com sandbox e defeitos simulados nos testes. | CLI `--strict --json` |
| `release_check.py` | Orquestrador dos **9 gates** oficiais em um comando. | `run_all(root, skip_ts, full_tests, smoke_tests)` · CLI `--json --skip-ts --smoke-tests \| --full-tests` |
| `run_tests.py` | Runner determinístico da suíte em **4 faixas** mutuamente exclusivas, com blindagem de archives. | `partition_modules(root)` · `run_tests(root, groups)` · CLI `--smoke \| --fast \| --render \| --all --json` |
| `archives_guard.py` | `ArchivesGuard` fotografa/restaura SHA-256 dos masters; `isolated_archives()` fornece `archives_dir` descartável sob `<RAIZ>/.workspace/tmp/`. | `ArchivesGuard(root)` · `isolated_archives(root)` · `snapshot(root)` |
| `studio_mcp_server.py` | Servidor MCP do Studio (ponte para ferramentas externas). **Nota:** o nome é `studio_mcp_server.py`; não existe `tools/studio_mcp.py`. | CLI do servidor MCP |
| `studio_connections.py` | Conexões e integrações do Studio, com provas HTTP locais. | API de conexões |
| `factory_cli.py` | Operação em lote: `list`, `render`, `pipeline`, `handoff`. Aceita `--archives-dir` para isolar masters em testes. | `cmd_render(..., archives_dir=None)` · `cmd_pipeline(..., archives_dir=None)` |
| `audio_tts.py` | Geração de WAV (ambient/narration bed) para tenants com áudio permitido. Bloqueia tenants `-an`. | `generate_audio(...)` |
| `bootstrap_ffmpeg.py` | Instala FFmpeg/FFprobe portáteis em `<MAIN_ROOT>/.workspace/tools/ffmpeg/`, idempotente. | `ensure_ffmpeg_tools(root, force=False)` |
| `srt_formatter.py` | Quebra determinística de linhas de SRT para legibilidade mobile (limite de 48 caracteres), preservando índices e timecodes. | CLI + sincronização de `artifacts.srt` |
| `static_cards.py` | Cards estáticos de Stories e Carrossel em PNG puro (stdlib). | CLI de geração |
| `handoff_bundler.py` | Pacote diário pós-aprovação: `POSTAGEM-MANUAL.md`, `copy-pronta.txt`, manifesto e mídia local. | CLI `factory_cli handoff` |
| `devlog_sync.py` | Consolida o registro de sessões no contexto do projeto, idempotente. | CLI `--json` |

---

## 4. Arquitetura de qualidade, auditoria e testes

### 4.1 Os 8 domínios do `release_audit.py`

| # | Domínio | Verifica |
| --- | --- | --- |
| 1 | `contratos_tenants` | 5 tenants válidos contra schema |
| 2 | `entregas_video` | manifestos, artefatos, política de áudio, hashes |
| 3 | `pacotes_sociais` | checklist + 3 `.md` por campanha, `autoPublish: false` |
| 4 | `derivados_multiformato` | 5 derivados por campanha, hashes e geometria |
| 5 | `calendario_utm` | slots, matriz UTM, contagens e parâmetros |
| 6 | `portal_revisao` | `portal-data.json` / `index.html`, sem caminho absoluto vazado |
| 7 | `higiene_git` | mídia não rastreada, `.gitattributes` com `eol=lf`, worktrees |
| 8 | `empacotamento_distribuicao` | bundles íntegros por SHA-256 (Etapa 11) |

Estado medido: **8/8 aprovados, 0 erros, 0 avisos** sob `--strict`.

### 4.2 Os 9 gates do `release_check.py`

> **Correção de contagem:** pedidos anteriores citam "8 gates". O orquestrador
> tem **9** desde a Etapa 13, quando o gate da suíte Python particionada foi
> inserido entre o empacotamento e o E2E.

| # | Gate | Conteúdo |
| --- | --- | --- |
| 1 | `higiene_git` | zero `.mp4`/`.wav`/`.zip` rastreados; `autoPublish: false` recursivo |
| 2 | `typescript` | `npm run build` + `npm test` em `platform/` (omitido com `--skip-ts`) |
| 3 | `tenant_validator` | 5 tenants |
| 4 | `editorial_qa` | 14 campanhas, 7 lentes, `--strict` |
| 5 | `workspace_doctor` | `--check` |
| 6 | `release_audit` | `--strict`, 8 domínios |
| 7 | `bundling` | `publish_bundler verify` dos bundles da estação |
| 8 | `unit_tests` | `run_tests.py --fast` (padrão), `--smoke` ou `--all` por flag |
| 9 | `e2e` | `unittest discover -s tests/e2e` |

### 4.3 As 7 lentes do `editorial_qa.py`

| # | Lente | Verifica |
| --- | --- | --- |
| 1 | `duracao_srt_manifest` | duração do manifesto vs. SRT vs. mídia |
| 2 | `legibilidade_mobile` | linhas de SRT ≤ 48 caracteres, blocos não vazios |
| 3 | `paridade_entregas` | artefatos de vídeo, cards e pacote social presentes e coerentes |
| 4 | `guardrails_cruzados` | violações de guardrail por tenant |
| 5 | `integridade_utf8` | UTF-8 válido, sem U+FFFD nem mojibake |
| 6 | `coerencia_hooks_calendario` | hooks do calendário vs. campanha |
| 7 | `aderencia_ui_labels` | `uiLabels` do brand-kit vs. rótulos usados |

Estado medido: **7/7 ok, 0 erros, 0 avisos**, 14 campanhas, 0 com problema.

### 4.4 As 4 faixas de execução do `run_tests.py`

Faixas **mutuamente exclusivas**; combinar duas retorna exit 2. Sem flag, o
padrão é `--fast`.

| Faixa | Composição | Módulos | Testes | Tempo medido |
| --- | --- | --- | --- | --- |
| `--smoke` | `fast` − `HEAVY_CONTRACT_MODULES` | **24** | **354** | **53,4 s** |
| `--fast` | unitários e contrato, sem render (gate oficial) | **28** | **422** | **375,4 s** |
| `--render` | render real via FFmpeg/FFprobe | **22** | não medido (§4.6) | não medido (§4.6) |
| `--all` | `fast` + `render` | **50** | soma | soma |

`HEAVY_CONTRACT_MODULES` (4 módulos que não renderizam mídia, mas criam sandboxes
Git completos, ponte Node/MCP ou servidores HTTP locais):
`test_release_audit`, `test_studio_mcp`, `test_studio_connections`, `test_editorial_qa`.

`SMOKE_MODULES` é **derivado** de `FAST_MODULES`, nunca uma lista paralela:

```python
SMOKE_MODULES = tuple(m for m in FAST_MODULES if m not in HEAVY_CONTRACT_MODULES)
```

Invariantes cobertas por `tools/tests/test_run_tests.py` (45 testes):
`smoke ⊂ fast` estritamente; `fast − smoke == HEAVY_CONTRACT_MODULES`;
`smoke ∩ render == ∅`; nenhum `test_*.py` órfão fora de `fast ∪ render`;
partição fechada (módulo novo sem classificação → erro de uso).

**Contrato JSON:** `{ok, mode, total, passed, failed, errors, skipped,
durationSeconds, modules}`. O payload também carrega chaves de diagnóstico
aditivas já existentes (`schemaVersion`, `generatedBy`, `root`, `results`,
`archivesGuard`, `partition`), consumidas por `release_check.gate_unit_tests`
e pelos testes de blindagem.

### 4.5 Meta de tempo do `--smoke`: não atingida, e por quê

A meta era 15–20 s. O medido foi **53,4 s**. Com a partição especificada
(`fast` menos exatamente aqueles 4 módulos), o piso é imposto por testes
legítimos que permanecem na faixa:

| Módulo | Tempo | Causa do custo |
| --- | --- | --- |
| `test_executive_summary` | ~10 s | geração real de relatórios e portais (30 testes) |
| `test_static_cards` | ~10 s | desenho real de PNG em stdlib |
| `test_run_tests` | ~5 s | subprocessos por faixa |
| `test_review_dashboard` | ~5 s | build real de portal |
| `test_workspace_doctor` | ~3,4 s | fixtures de workspace |

Otimização aplicada nesta entrega: `test_executive_summary` memoiza o QA
editorial do acervo real (somente leitura e invariante entre testes), que antes
era reexecutado 5× por chamada de `collect_inputs`. Caiu de ~20 s para ~10 s,
sem stubbar resultado — as asserções continuam verificando o acervo verdadeiro.

Atingir 15–20 s exigiria esvaziar testes legítimos ou redefinir a composição da
faixa, quebrando o contrato. O ganho real de `smoke` sobre `fast` é de **~7×**,
que é o valor operacional entregue.

### 4.6 Faixa `--render`

22 módulos. **Tempo não medido nesta entrega.** A execução foi iniciada e
interrompida antes de concluir, para não competir com os gates finais: os testes
de render criam e removem diretórios de entrega temporários dentro de
`02-reels-shorts/deliveries/`, o que tornaria `editorial_qa` e `release_audit`
não-determinísticos se rodassem em paralelo. Não há número parcial publicado —
um tempo incompleto seria enganoso.

Para medir, execute isoladamente, sem outros gates em paralelo:

```bash
python tools/run_tests.py --render --json
```

A faixa exige FFmpeg/FFprobe portáteis instalados. Sem eles, os testes se
auto-omitem via `skipUnless`, o que **não** equivale a aprovação do pipeline:
`skipped > 0` nessa faixa significa cobertura ausente, não sucesso.

Após a interrupção, a integridade foi reconferida: nenhum processo órfão, nenhum
diretório de entrega temporário remanescente e `workspace_doctor --check` com
0 erros e 84/84 mídias verificadas — os masters não foram afetados, porque os
testes de render usam `archives_dir` isolado.

### 4.7 Blindagem de `.workspace/archives/`

Toda execução do runner, em qualquer faixa, roda dentro de
`archives_guard.ArchivesGuard`: fotografa os SHA-256 dos 84 arquivos antes do
run, guarda cópia integral e, ao sair, restaura o que foi alterado ou removido
e descarta mídia nova criada pelo teste. Temporários sempre sob
`<RAIZ>/.workspace/tmp/`.

Causa raiz histórica das divergências: `test_audio_tts.py` e
`test_factory_cli.py` chamavam o pipeline canônico sem `archives_dir` isolado e
sobrescreviam os masters reais. Corrigido em duas camadas — `archives_dir`
isolado por teste **e** guard em `setUpModule`, de modo que a proteção vale
também em `unittest` direto, fora do runner.

---

## 5. Fluxo operacional ponta a ponta (Etapas 8 a 13)

```
métricas UTM
   └─> comparativo Hook A/B híbrido (teste z)
         └─> detecção temporal de fadiga
               └─> tenantBenchmarks isolados
                     └─> promoção assistida (promote-hook)
                           └─> empacotamento bit-determinístico
                                 └─> reconciliação pós-publicação
                                       └─> relatório executivo semanal
                                             └─> auto-reparo de mídia local
```

### 5.1 Comparativo Hook A/B híbrido (Etapa 8)

Camada estatística sobre o comparativo descritivo A/B. Teste **z bilateral de
duas proporções** com variância agrupada:

- `p = math.erfc(|z| / sqrt(2))`, `z` arredondado a 4 casas, `p` a 6.
- Vencedor exige **`|z| ≥ 1.96` e `p < 0.05`**; caso contrário `empate_tecnico`.
- Amostra mínima: `DEFAULT_MIN_SESSIONS = 100`, `DEFAULT_MIN_CONVERSIONS = 5`;
  abaixo disso, `amostra_insuficiente`.
- Classificações: `vencedor_A`, `vencedor_B`, `empate_tecnico`, `amostra_insuficiente`.
- Saída em `rankings.hookComparison.byCampaign` e `.byTenant`, com `zScore`,
  `pValue`, `significant`, `classification`, `classificationReason`.

### 5.2 Detecção temporal de fadiga (Etapa 9)

`_detect_hook_fatigue(conversions_w1, sessions_w1, conversions_w2, sessions_w2)`
compara Onda 1 vs. Onda 2 e retorna `fatigueStatus`, `fatigueZScore`,
`fatiguePValue`, `fatigueDetected`, `fatigueReason`.

- `fadiga_detectada` quando **`z ≥ 1.96` e `p < 0.05`** (z positivo: a ordem
  w1 vs. w2 codifica a queda).
- Exige ≥ 1 sessão e ≥ `min_conversions` conversões em **ambas** as janelas;
  senão `amostra_insuficiente`. Caso estável: `estavel`.

### 5.3 Benchmarks isolados por tenant (Etapa 9)

`rankings.tenantBenchmarks.byTenant[]` com `sessions`, `conversions`,
`conversionRatePct`, `engagedRatePct`, `slots`, `abWinRatePct`,
`abCampaignsTotal`, `abCampaignsWins` e o bloco `hooksComFadiga*`.

### 5.4 Promoção assistida (Etapa 10)

`approval_cli promote-hook --dry-run` (padrão) planeja; `--apply` grava a entrada
em `promotionHistory` **somente após** passar o gate `editorial_qa --strict`.
Registra `promotedVariant`, `promotedBy`, `promotedAt`, `zScore`, `pValue`,
`fatigueStatus`, `fatigueDetected`, `sourceReport`, `classificationReason`.
Não publica nem altera calendário.

### 5.5 Empacotamento bit-determinístico (Etapa 11)

`publish_bundler pack --tenant <id> --slug <slug>` gera ZIP com entradas em
ordem lexicográfica, manifesto com SHA-256 por item e do arquivo, e
`approvalStatus`. Gate de aprovação: `ajuste` → `SLOT_EM_AJUSTE`; não aprovado →
`CAMPANHA_NAO_APROVADA`, salvo `--allow-unapproved`, que carimba
`PREVIA_NAO_APROVADA`. `verify` reconfere hash do ZIP, hash por item, ordem das
entradas e `autoPublish: false`.

### 5.6 Reconciliação pós-publicação (Etapa 12)

`utm_report_importer --reconcile-bundles` cruza os manifestos de
`.workspace/bundles/<tenant>/<slug>/*-manifest.json` com o desempenho UTM e
produz `bundleAttribution`:

- Status: `reconciliado`, `aguardando_metricas`, `divergencia_tenant`,
  `nao_elegivel_para_PREVIA_NAO_APROVADA`.
- Métricas: `impressions` (Σ sessões), `clicks` (Σ sessões engajadas),
  `ctr`, `conversionRate`, `observedUpliftPct` (uplift vs. a taxa de referência
  do tenant) e `winnerSustained`.

### 5.7 Relatório executivo semanal (Etapa 13)

`executive_summary --all` gera, por tenant, JSON + Markdown em
`.workspace/reports/<tenantId>/`, com governança (`tenantId`, `brandName`,
`generatedAt` UTC, `weekFilter`, `autoPublish: false`), saúde editorial,
A/B e fadiga, entregas e atribuição, e plano de ação priorizado. **Somente
leitura**: sem relatório UTM ou sem bundles, as seções declaram `sem dados`
com o motivo, em vez de recalcular estatística. O portal expõe o digest em
`executiveSummary`.

### 5.8 Auto-reparo cirúrgico de mídia (Etapa 13)

`workspace_doctor --repair` (dry-run por padrão; `--dry-run` explicita,
`--apply` grava), com `--slug` / `--tenant`:

1. **Master divergente com cópia versionada intacta** → restaura byte a byte de
   `02-reels-shorts/deliveries/<tenant>/<slug>/<slug>.mp4` quando o SHA-256 dela
   confere com o declarado. Estratégia `restore-from-delivery`, sem render.
2. **Master divergente sem cópia intacta** → re-renderiza o slot pelo pipeline
   canônico em staging isolado sob `.workspace/tmp/`, e **só promove** se o
   SHA-256 produzido for igual ao declarado.
3. **Apenas derivados divergentes** → regenera somente os formatos afetados via
   `derivative_formats`, e apenas com master íntegro.

Fail-closed: `INSUMO_AUSENTE`, `MASTER_NAO_REPRODUTIVEL`,
`FFPROBE_DIVERGENTE_POS_REPARO`, `DERIVADO_NAO_REPRODUTIVEL`. Nada é gravado e o
motivo vai para `skippedItems` / `remainingErrors`. Não re-declara manifesto
versionado, não altera calendário, aprovação ou UTM.

---

## 6. Armadilhas conhecidas de contrato e nomenclatura

Pontos que já causaram erro real de leitura ou integração. Todos verificados
contra o código nesta consolidação.

| # | Armadilha | Realidade | Consequência se ignorada |
| --- | --- | --- | --- |
| 1 | `abWinRatePct` parece percentual | É **fração 0..1** (`round(wins/total, 4)`), apesar do sufixo `Pct` | Ler `0.5` como 0,5% em vez de 50%. `executive_summary` expõe `benchmarkAbWinRate` com `fraction` e `percent` lado a lado |
| 2 | Fadiga em `tenantBenchmarks` | Campos com prefixo **`hooksComFadiga*`** (`hooksComFadiga`, `...Status`, `...ZScore`, `...PValue`, `...Reason`), não `fatigue*` | Buscar `fatigueDetected` no benchmark retorna `None`; os `fatigue*` vivem nos **slots do calendário** e no detector |
| 3 | Chave de campanha no comparativo A/B | `hookComparison.byCampaign[]` usa **`campaign`**, não `slug` | Join por `slug` não casa nenhuma linha. Slots, bundles e calendario usam `slug` |
| 4 | Dois schemas de `promotionHistory` | `approval_cli.cmd_promote_hook` grava `promotedVariant` / `promotedBy` / `promotedAt`; `publish_bundler` sintetiza `decisao` / `reviewer` / `updatedAt` | `_promotion_history_has_winner` só reconhece `promotedVariant` ou `decisao ∈ ("A","B")`; histórico vindo só de aprovações yields `winnerSustained: False` |
| 5 | `manifest.json` vs `delivery-manifest.json` | `preset_runner` grava **`manifest.json`** + cópia em archives; `render_local.run_render` grava **`delivery-manifest.json`** e nunca toca archives | Usar `render_local` para "re-renderizar o master" não reproduz o artefato declarado. Não existe `tools/batch_render.py` |
| 6 | `winnerSustained` muda de lugar | Dentro de `metrics` quando `reconciliado`; **top-level `None`** quando `aguardando_metricas`; **ausente** em `PREVIA_NAO_APROVADA` | Indexação direta levanta `KeyError` |
| 7 | `editorial_qa` usa `tenant`, não `tenantId` | `campaigns[]` traz `{tenant, slug, problems: int, ok}`; `problems` é **contagem**, não lista | Os problemas reais só estão em `checks[].problems` |
| 8 | `aprovadas` vs `aprovado` | Sumário de `approval_cli.cmd_status` usa `aprovadas` (contagem); o valor de decisão é `"aprovado"` | Comparar contagem com string |
| 9 | `verify_bundle` tem dois formatos de retorno | Quando o manifesto falta, omite `manifestPath`, `declaredSha256`, `itemCount`, `zipEntryCount` | Usar `.get()` sempre |
| 10 | Dicts com chave-tupla | `load_calendar.index`, `load_utm_report.byCampaign`, `load_bundle_attribution.byKey` usam tuplas como chave | Não serializam em JSON diretamente |
| 11 | `generate_calendar` descarta atribuição | Só `build_editorial_calendar` aceita `bundle_attribution`; a CLI não tem a flag | Atribuição não chega ao calendário por esse caminho |
| 12 | `campaign_calendar` não usa `aprovado/aguardando/ajuste` | Só `statusEditorial = "aguardando_aprovacao_titular"`. O vocabulário de decisão vive em `approval_cli` e `review_dashboard` | Procurar decisão no calendário |
| 13 | `manifest["config"]` é string | Caminho relativo do JSON de campanha, não objeto | `.get("path")` sobre string levanta `AttributeError` |
| 14 | Render não é byte-reprodutível entre versões do código | O comando não usa `-bitexact` nem `-threads 1`; o nº de threads entra no bitstream. Hash declarado pode ser de código anterior | Re-render não restaura hash antigo; por isso o reparo prefere a cópia versionada intacta e é fail-closed |
| 15 | Testes de render têm dependência de CWD | `preset_runner` resolve `fixturePath` relativo ao CWD; rodar `unittest` de dentro de `tools/tests/` falha com `FileNotFoundError` | Rodar sempre da raiz: `python -m unittest discover -s tools/tests` |
| 16 | `.workspace/reports/` precisa de exclude local | A regra vive em `.git/info/exclude`, **local por estação** | Em outra máquina os relatórios aparecem em `git status`. `.workspace/bundles/` e `.workspace/snapshots/` têm a mesma lacuna |

---

## 7. Roadmap sugerido para a Etapa 14

Propostas, não compromissos. Nenhuma delas está implementada.

### 7.1 Onboarding automatizado de tenants — `tenant_scaffolder.py`

Hoje cadastrar um nicho é manual, guiado por `docs/guia-novo-nicho.md`. Um
scaffolder declarativo reduziria o passo a ~1 comando:

- Entrada: `tenant_id`, `brandName`, domínio, paleta, `uiLabels`, política de
  áudio, preset padrão e guardrails.
- Gera `tenants/<id>/brand-kit.json`, `guardrails.json`, fixture editorial e a
  primeira campanha, todos válidos contra os schemas existentes.
- Valida com `tenant_validator` antes de gravar e roda `editorial_qa --tenant`
  no resultado; fail-closed se qualquer lente reprovar.
- **Restrição:** o calendário tem mínimo estrutural de semanas
  (`ceil(n/4) + ceil(n/6)`). Adicionar tenant/campanha muda esse mínimo; o
  scaffolder deve **reportar** o impacto e exigir decisão do titular, nunca
  reescrever datas de calendário automaticamente.

### 7.2 Simulação de capacidade de calendário

Ferramenta de planejamento que, dado um conjunto de tenants/campanhas e uma
data inicial, calcula semanas necessárias, distribuição por canal/formato e
colisões de janela BRT **sem gravar** o calendário. Saída: relatório de
capacidade com o mínimo de semanas e os gargalos por dia. Reutilizaria
`build_editorial_calendar` em modo dry-run.

### 7.3 Evoluções operacionais

- **Gate de testes em três níveis no CI:** `smoke` em todo push, `fast` em PR,
  `all` em release — hoje o CI roda `fast` sempre.
- **Determinismo de render:** avaliar `-threads 1` + `-flags +bitexact` para
  tornar o master reprodutível entre estações, permitindo que o reparo por
  re-render restaure o hash declarado. Mudaria os hashes de todos os masters:
  exige re-release planejado e autorização explícita.
- **Snapshot antes de release:** `workspace_doctor snapshot export` já existe;
  torná-lo passo obrigatório do checklist daria restauração byte-exata sem
  depender da cópia versionada.
- **Exclude portável:** documentar em `docs/guia-novo-nicho.md` o bloco completo
  de `.git/info/exclude` (incluindo `reports/`, `bundles/`, `snapshots/`) para
  que toda estação nova nasça com a higiene correta.
- **`--list` no runner:** exposição explícita da partição sem executar testes,
  útil para auditoria de composição em CI.

---

## 8. Evidência desta execução

Gates executados nesta entrega, todos na raiz do checkout:

| Verificação | Resultado |
| --- | --- |
| `run_tests.py --smoke --json` | ok, 24 módulos, **354/354**, 0 falhas/erros/pulados, 53,4 s |
| `run_tests.py --fast --json` | ok, 28 módulos, **422/422**, 0 falhas/erros/pulados, 375,4 s |
| `python -m unittest tools/tests/test_run_tests.py` | **45/45** ok |
| `workspace_doctor.py --check --json` | **0 erros, 0 avisos**, 84/84 mídias verificadas |
| `editorial_qa.py --all --strict --json` | **0 erros, 0 avisos**, 14 campanhas, 7/7 lentes |
| `release_audit.py --strict --json` | **8/8 domínios**, 0 erros, 0 avisos |
| `git status --short` | limpo; nenhum artefato de `.workspace/` rastreado |

Artefatos locais de evidência (não versionados):
`.workspace/logs/etapa-13-1/{smoke,fast}.json`. A faixa `--render` não tem
medição concluída nesta entrega (§4.6).

---

## 9. Referências

- [AGENTS.md](AGENTS.md) — regras de operação, portabilidade, `.workspace/` e autorizações.
- [docs/arquitetura-fabrica.md](docs/arquitetura-fabrica.md) — arquitetura, contratos e matriz de execução da suíte.
- [docs/guia-operacional-titular.md](docs/guia-operacional-titular.md) — rotina diária e semanal, faixas de teste e reparo de mídia.
- [docs/analytics-utm-playbook.md](docs/analytics-utm-playbook.md) — eventos por nicho e rotina de UTM.
- [docs/guia-novo-nicho.md](docs/guia-novo-nicho.md) — cadastro manual de novo tenant.
- [docs/contexto/README.md](docs/contexto/README.md) — índice de contexto compartilhado.
- [WORKFLOW.md](WORKFLOW.md) — fluxo editorial e regra de vídeo sem áudio.
- [contexto_projeto.md](contexto_projeto.md) — registro histórico de sessões (anterior a esta consolidação).