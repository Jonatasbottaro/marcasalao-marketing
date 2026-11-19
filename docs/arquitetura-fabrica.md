# Arquitetura da Fábrica de Vídeo Multi-Tenant

Documento mestre do pipeline de produção de vídeo programático multi-tenant (Etapas 2 a 4). Público: operadores e agentes que executam, estendem ou auditam a fábrica. A fonte da verdade é o código; este documento descreve o comportamento comprovado pelos testes e pelo CI.

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Camadas do pipeline](#2-camadas-do-pipeline)
3. [Regras operacionais e guardrails](#3-regras-operacionais-e-guardrails)
4. [Fluxo operacional de ponta a ponta](#4-fluxo-operacional-de-ponta-a-ponta)
5. [Testes e CI](#5-testes-e-ci)
6. [Referências](#6-referências)

---

## 1. Visão geral

A fábrica transforma **contratos JSON versionados** (brand-kit, guardrails, fixture editorial e campanha) em **pacotes de vídeo prontos para publicação manual**, para N marcas ("tenants") sem alterar o motor de render. Cada etapa é determinística, validada por schema e auditável por hash: a mesma configuração produz os mesmos bytes em qualquer estação.

Invariante de entrega (por campanha, em `02-reels-shorts/deliveries/<tenant>/<slug>/`):

| Artefato | Papel | Versionado no Git |
| --- | --- | --- |
| `<slug>.mp4` | Vídeo vertical 1080×1920@30 H.264/yuv420p | Não (`*.mp4` ignorado; hash e ffprobe no manifesto) |
| `<slug>.srt` | Legendas sincronizadas | Sim |
| `<slug>_narracao.txt` | Texto de narração para áudio externo | Sim |
| `preview-storyboard.png` | Storyboard 2×2 (quadros em 2/8/16/24 s) | Sim |
| `manifest.json` | Hashes SHA-256, bytes, ffprobe, comando reproduzível | Sim |
| `derivatives.json` | Declaração dos derivados (cover, 1:1, 16:9) com SHA-256, bytes e comando reproduzível | Sim |

Pacote social correspondente em `04-legendas/pacotes-publicacao/<tenant>/<slug>/` (`instagram-reels.md`, `youtube-shorts.md`, `facebook-reels.md`, `checklist-publicacao.json` com `autoPublish: false`). **Nada publica sozinho**: publicação é sempre manual e exige autorização específica.

```
schemas/ ──┐
           ├──> tenant_validator ──> preset_runner ──(+ audio_tts*)──> deliveries/<tenant>/<slug>/
tenants/ ──┘            │                                                       │
                        │             factory_cli (lote: list / render)         │
                        │                                                       v
                        │                                     derivative_formats (cover, 1:1, 16:9)
                        │                                                       │
                        │                                                       v
                        ├──────────────────────────────> publish_pack (pacotes sociais + checklist)
                        │                                                       │
                        │                                                       v
                        ├──────────────────────────────> campaign_calendar (calendário + matriz UTM)
                        │                                                       │
                        │                                                       v
                        └──────────────────────────────> review_dashboard (portal de revisão humana)
                                                                                │
                                                                                v
                                                        release_audit (gate de release, 7 domínios)

devlog_sync (transversal): consolida os devlogs de sessão no contexto_projeto.md
```

\* `audio_tts` só participa de tenants com `allowAudioTrack: true` (hoje apenas `multitrack-hub`).

## 2. Camadas do pipeline

### 2.1 Contratos e schemas (`schemas/`)

- `brand-kit.schema.json` — identidade, paleta, tipografia, overlay de cabeçalho, estilo de legenda, preset padrão e UTMs da marca.
- `guardrails.schema.json` — alegações proibidas (`forbiddenClaims`), elementos de UI proibidos e política de áudio (`audioPolicy.allowAudioTrack`, `requireSrt`, `requireExternalNarration`).

Validação por JSON Schema sem dependências externas (implementação em `tools/tenant_validator.py`). O `.gitattributes` garante `text eol=lf` para `tenants/**/*.json` e para os artefatos de `02-reels-shorts/` e `04-legendas/`, mantendo os hashes SHA-256 idênticos entre estações Windows e CI Linux.

### 2.2 Tenants (`tenants/<tenantId>/`)

```
tenants/<tenantId>/
├── brand-kit.json          # identidade visual e padrões da marca
├── guardrails.json         # proibições e política de áudio
├── fixtures/               # fixture editorial (dados fictícios plausíveis)
│   └── fixture-editorial-<tenantId>.json
└── campaigns/              # contratos de campanha (uma por vídeo)
    └── <slug>.json
```

Os 4 tenants atuais (8 campanhas):

| Tenant | Marca | Preset | Domínio | Faixa de áudio | Campanhas |
| --- | --- | --- | --- | --- | --- |
| `marca-salao` | Marca Salão | `saas-demo` | marcasalao.com.br | Proibida (`-an`, narração externa obrigatória) | 2 |
| `multitrack-hub` | Multitrack Hub | `shorts-completo` | multitrackhub.com.br | Permitida (trilha opcional via `audio_tts`) | 3 |
| `meu-salao` | Meu Salão | `saas-demo` | meusalao.com.br | Proibida | 2 |
| `estudio-flow` | Estúdio Flow | `saas-demo` | estudioflow.com.br | Proibida | 1 |

Presets: `saas-demo` (cenas de app B2B/agenda/booking) e `shorts-completo` (hook, catálogo/projetos, métricas, cards e CTA). Fixtures não podem conter placeholders de teste técnico e, no preset `saas-demo`, devem manter as chaves estruturais lidas pelo motor (`profissionais`, `servicos`, `agenda.atendimentos`, `booking.rota`) mesmo quando adotam nomes próprios do nicho.

### 2.3 `tools/tenant_validator.py` — validação de contratos

Ponto único de leitura validada de brand-kit + guardrails + fixture. API usada por todos os módulos:

```python
ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=REPO_ROOT, strict=True)
```

- `list_tenants(root)` — descobre tenants sob `tenants/`.
- `load_and_validate_tenant(tenant_id, root, strict)` — valida os três contratos, cruza `tenantId` com a pasta e o fixture, aplica guardrails de texto; com `strict=True` levanta `TenantContractError` em qualquer erro.
- `validate_text_against_guardrails(...)` — usada pelo `publish_pack` para auditar legendas antes de gravar.

CLI: `python tools/tenant_validator.py --all --json` (exit 1 em falha de validação, 2 em uso).

### 2.4 `tools/preset_runner.py` — motor de render

Renderiza uma campanha (`--tenant --config --output-dir [--audio] [--json]`):

1. Carrega o tenant validado (`load_and_validate_tenant(..., strict=True)`) e o contrato da campanha.
2. Desenha cada cena como PNG (brand-kit, fixture e textos da campanha).
3. Monta o vídeo com FFmpeg (concatenação por cena, escala/pad 1080×1920, legendas queimadas do SRT).
4. Política de áudio: tenants com `allowAudioTrack: false` exportam **sem faixa de áudio** (`-an`, 0 streams no ffprobe) e recusam `--audio`; tenants permitidos podem receber trilha via `--audio`.
5. Gera SRT, narração TXT, storyboard 2×2 e `manifest.json` com SHA-256/bytes/ffprobe/comando reproduzível.
6. Promove a entrega de forma transacional: falha em qualquer etapa preserva a entrega anterior.

### 2.5 `tools/audio_tts.py` — trilhas (Agente 2, Etapa 3)

Gera trilhas `.wav` (30 s, 44100 Hz, estéreo) **somente para tenants com `allowAudioTrack: true`** (hoje `multitrack-hub`); recusa imediatamente tenants que proíbem áudio (trava de segurança antes de qualquer render). Modos sem APIs pagas: `ambient-bed` (cama sonora sintetizada via FFmpeg `lavfi`, normalizada para -22 LUFS) e `narration-bed` (TTS local opcional sobre a cama, com fallback seguro). Saída alimenta o `--audio` do `preset_runner`.

### 2.6 `tools/factory_cli.py` — operação em lote

- `list [--tenant <id>] --json` — descoberta de tenants/campanhas.
- `render [--tenant <id> | --all] [--report <caminho>] --json` — renderiza em lote, gravando transacionalmente em `02-reels-shorts/deliveries/<tenant>/<slug>/`, arquivando a cópia do vídeo em `.workspace/archives/<slug>/` e consolidando o índice em `02-reels-shorts/deliveries/factory-report.json` (ou no caminho de `--report`, recomendado em worktrees paralelas para não disputar o índice compartilhado).

### 2.7 `tools/publish_pack.py` — pacotes sociais (Agente 3, Etapa 3)

Lê a entrega renderizada + brand-kit (domínio, UTMs) + guardrails e gera os textos por rede (`instagram-reels.md`, `youtube-shorts.md`, `facebook-reels.md`) e o `checklist-publicacao.json` com `autoPublish: false`. Todas as legendas são auditadas contra `forbiddenClaims`/`forbiddenUiElements` antes de gravar; texto proibido aborta o pacote sem gravar parcial. CLI: `python tools/publish_pack.py --all` ou `--tenant <id> --slug <slug>`.

> **Efeito colateral conhecido:** re-executar `publish_pack` (ou sua suíte de testes) numa estação **sem** os `.mp4` em disco re-verifica e regrava `sha256_disk_ok: false` nos checklists versionados. Restaure com `git checkout -- 04-legendas/` nesses casos; o valor `true` reflete a estação que renderizou. O `release_audit` trata vídeo ausente como **aviso**, não falha.

### 2.8 `tools/release_audit.py` — gate de release em 7 domínios (Agente 4, Etapa 4)

Auditor final de prontidão em uma passada (`python tools/release_audit.py [--strict] [--json] [--report-out <arquivo>] [--root <raiz>]`; API `run_release_audit(root, strict=False) -> dict`, relatório `schemaVersion: 2` com `domains[]` e `summary`). Cada problema carrega `severity` (`error` | `warning`), `code` e `message`; `error` reprova sempre, `warning` só reprova com `--strict`.

| # | Domínio (`id`) | O que verifica | Erros típicos |
| --- | --- | --- | --- |
| 1 | `contratos_tenants` | ≥ 4 tenants válidos via `tenant_validator` (brand-kit, guardrails, fixture; `strict=False`, agregando erros) | `TENANT_INVALIDO`, `TENANTS_INSUFICIENTES` |
| 2 | `entregas_video` | Por campanha: diretório, `manifest.json`, `<slug>.srt`, `<slug>_narracao.txt`, `preview-storyboard.png` com SHA-256 e bytes conferidos em disco; política de áudio simétrica (`allowAudioTrack: false` ⇒ `ffprobe.audioStreams == 0`; `true` ⇒ `>= 1`) | `DELIVERY_DIR_AUSENTE`, `MANIFEST_AUSENTE`, `HASH_DIVERGENTE`, `TAMANHO_DIVERGENTE`, `ARQUIVO_AUSENTE`, `POLITICA_AUDIO_DESCUMPRIDA` |
| 3 | `pacotes_sociais` | `checklist-publicacao.json` com `autoPublish: false` e `guardrailsAudited: true`, os três textos por rede e o SHA-256 das mídias declaradas | `PACOTE_AUSENTE`, `AUTO_PUBLICACAO_ATIVO`, `GUARDRAILS_NAO_AUDITADOS`, `ARQUIVO_PACOTE_AUSENTE` |
| 4 | `derivados_multiformato` | `derivatives.json` por campanha com as três declarações (`cover`, `square`, `wide`) e hash; derivado presente em disco tem SHA-256 conferido | `DERIVADO_DECLARACAO_AUSENTE`, `DERIVADO_SEM_HASH`, `HASH_DIVERGENTE` |
| 5 | `calendario_utm` | `calendario-editorial.json` (estrutura, `totalSlots` == `len(slots)`, `autoPublish: false` no topo e em cada slot), `.md` e `matriz-utm-consolidada.csv` | `CALENDARIO_INVALIDO`, `SLOTS_CONTAGEM_DIVERGENTE`, `AUTO_PUBLICACAO_ATIVO` |
| 6 | `portal_revisao` | `05-review-portal/` com `index.html`, `portal-data.json`, `README.md`; varredura de caminhos absolutos de estação vazados no JSON/HTML | `CAMINHO_ABSOLUTO_VAZADO` |
| 7 | `higiene_git` | `git ls-files "*.mp4" "*.wav"` vazio; `.gitattributes` com regra `eol=lf` cobrindo `.json`, `.srt`, `.md` e `.html`; worktrees históricas (`prova-campanha-conclusao`, `studio-package-verify2`) preservadas | `MIDIA_RASTREADA`, `GITATTRIBUTES_SEM_EOL_LF`, `GITATTRIBUTES_EXT_SEM_EOL_LF`, `WORKTREE_REGISTRADA_SEM_DIRETORIO` |

Avisos (`warning`, não reprovam no modo normal; **reprovam com `--strict`**): `DERIVATIVES_AUSENTE`, `CALENDARIO_AUSENTE`, `MATRIZ_UTM_AUSENTE`, `PORTAL_ARQUIVO_AUSENTE` e `WORKTREE_ORFA` — ou seja, artefatos de consolidação ainda ausentes e worktree histórica com diretório sem registro.

**Mídia local da estação não é defeito:** o `<slug>.mp4` da entrega e os derivados sob `.workspace/archives/<slug>/derivatives/` não são versionados; quando ausentes em disco não geram problema (o manifesto e a declaração preservam hash, ffprobe e comando reproduzível), e quando presentes têm o SHA-256 conferido. Por isso o modo normal roda em qualquer estação ou checkout novo do CI, e o `--strict` só exige o que está declarado no Git.

`--report-out <arquivo>` grava o relatório JSON (UTF-8, LF) em caminho obrigatoriamente contido sob a raiz; caminho externo é recusado com `PATH_OUTSIDE_ROOT`. A saída do CLI é UTF-8 mesmo no Windows, onde o encoding padrão de pipe é o da locale.

Exit codes: `0` aprovado; `1` reprovado; `2` erro de uso/execução.

### 2.9 `tools/devlog_sync.py` — registro de sessões (Agente 4, Etapa 4)

Consolida devlogs `.workspace/devlogs/etapa*-agente*.md` no `contexto_projeto.md` (Seção 1 "Estado atual" + Seção 7 "Histórico de sessões"), com ordenação numérica por `(etapa, agente)`, idempotência por marcador `<!-- devlog-sync:<arquivo> -->` e retrocompatibilidade total com os registros da Etapa 3. `--pattern` restringe a descoberta (padrão `etapa*-agente*.md`); o resultado JSON reporta `pattern` e a etapa/agente de cada entrada. A consolidação é idempotente: re-execuções não duplicam entradas já aplicadas. CLI: `python tools/devlog_sync.py [--pattern <glob>] [--json]`.

### 2.10 `tools/derivative_formats.py` — derivados multiformato (Agente 1, Etapa 4)

Parte dos MP4s verticais arquivados em `.workspace/archives/<slug>/<slug>.mp4` (mais o `manifest.json` da entrega e o brand-kit do tenant) e gera, por campanha, em `.workspace/archives/<slug>/derivatives/`:

- `<slug>-cover.png` — frame representativo (segundo 2.0, ou metade da duração em fontes mais curtas) em 1080×1920, com moldura sutil na cor primária do brand-kit.
- `<slug>-1x1.mp4` — 1080×1080@30 H.264/yuv420p, com fundo desfocado e escurecido derivado do próprio vídeo e o 9:16 centralizado.
- `<slug>-16x9.mp4` — 1920×1080@30, mesma composição.

Grava também `derivatives.json` **na entrega versionada** (`02-reels-shorts/deliveries/<tenant>/<slug>/`), declarando `source` (caminho, SHA-256, ffprobe) e os três derivados (`cover`, `square`, `wide`) com caminho, SHA-256, bytes e comando reproduzível — é essa declaração que o domínio 4 do `release_audit` confere. CLI: `python tools/derivative_formats.py (--all | --tenant <id> [--campaign <slug>]) [--json]`. Como os MP4s de origem são locais da estação, a geração exige a estação que renderizou; a declaração versionada preserva a integridade para as demais.

### 2.11 `tools/campaign_calendar.py` — calendário editorial e matriz UTM (Agente 3, Etapa 4)

Lê os tenants validados e os `checklist-publicacao.json` gerados pelo `publish_pack` e distribui as campanhas num cronograma intercalado: até 2 campanhas por dia, nunca duas do mesmo tenant no mesmo dia (seleção gulosa pelos tenants com mais campanhas restantes), cada campanha cobrindo os 3 canais configurados (Instagram Reels, YouTube Shorts, Facebook Reels) em suas janelas horárias. Todos os slots nascem com `autoPublish: false` e `statusEditorial: "aguardando_aprovacao_titular"` — o calendário é proposta, nunca publicação.

Saídas: `04-legendas/calendario-editorial.json` (estrutura completa dos slots, com `audioPolicy`, `utmUrl` e contagens) e `04-legendas/calendario-editorial.md` (cronograma cronológico, checklist e matriz consolidada das URLs UTM). CLI: `python tools/campaign_calendar.py --start-date YYYY-MM-DD [--json]`.

> **Pendência de consolidação:** o arquivo separado `04-legendas/matriz-utm-consolidada.csv`, esperado pelo domínio 5 do `release_audit`, está em produção pelo Agente 3 e **ainda não consta na main**. Enquanto ausente, o domínio 5 reporta o aviso `MATRIZ_UTM_AUSENTE`: o modo normal segue aprovado e o `--strict` reprova.

### 2.12 `tools/review_dashboard.py` — portal de revisão humana (Agente 2, Etapa 4)

Consolida tenants (brand-kit + guardrails), entregas (manifesto, SRT, narração, storyboard) e pacotes sociais (checklist + os três textos por rede) num portal estático em `05-review-portal/`: `index.html` (dados embutidos, abre direto via `file://`), `portal-data.json` e `README.md`. O build é determinístico — não grava timestamps e produz bytes idênticos para os mesmos insumos, de modo que o portal versionado é o mesmo em qualquer estação.

CLI: `python tools/review_dashboard.py --build [--json]` para gerar e `python tools/review_dashboard.py --serve [--port 8765]` para revisar no navegador. O portal é somente leitura: nenhuma ação dele publica, agenda ou altera artefato. O domínio 6 do `release_audit` exige os três arquivos e varre o JSON/HTML em busca de caminhos absolutos de estação vazados (`CAMINHO_ABSOLUTO_VAZADO`).

## 3. Regras operacionais e guardrails

- **Vídeo sem áudio (regra do titular):** para Marca Salão (e tenants com `allowAudioTrack: false`), exportar **sem faixa de áudio** (`-an`), com legendas queimadas e sincronizadas, SRT e narração TXT separados para geração de áudio em ferramenta externa. Vídeos de demonstração/teste não são campanhas aprovadas.
- **Publicação sempre manual:** `autoPublish: false` é verificado pelo gate; nenhuma etapa publica, agenda ou cria rascunho por conta própria.
- **Vídeo fora do Git, integridade no manifesto:** `*.mp4` é ignorado pelo `.gitignore`; o `manifest.json` preserva SHA-256, bytes, ffprobe e o comando reproduzível; a cópia local fica em `.workspace/archives/<slug>/` (não sincronizada entre estações).
- **Portabilidade entre estações:** a raiz oficial é o checkout principal (`git rev-parse --show-toplevel`); tudo dentro de `<RAIZ>`, auxiliares em `<RAIZ>/.workspace/`, alinhamento exclusivamente por Git. Ver `AGENTS.md`.
- **Worktrees:** apenas em `<RAIZ>/.workspace/worktrees/`; worktrees históricas de prova são preservadas e auditadas pelo gate.
- **Hashes estáveis:** `eol=lf` no `.gitattributes` para JSONs/SRT/TXT do pipeline garante hashes idênticos entre Windows e CI Linux.

## 4. Fluxo operacional de ponta a ponta

```bash
# 0. Alinhar a estação
git fetch origin --prune && git pull --ff-only

# 1. Validar contratos (4 tenants)
python tools/tenant_validator.py --all --json

# 2. (Opcional, só multitrack-hub) trilha de áudio
python tools/audio_tts.py --tenant multitrack-hub \
  --output .workspace/tmp/audio-mth/bed-30s.wav --duration 30 --mode ambient-bed

# 3. Renderizar (lote; use --report em worktree paralela)
python tools/factory_cli.py list --json
python tools/factory_cli.py render --all --json
#   ou campanha individual:
python tools/preset_runner.py --tenant marca-salao \
  --config tenants/marca-salao/campaigns/camp-saas-demo-marca-salao-001.json \
  --output-dir 02-reels-shorts/deliveries/marca-salao/camp-saas-demo-marca-salao-001

# 4. Derivados multiformato (cover, 1:1, 16:9) — exige os MP4s arquivados na estação
python tools/derivative_formats.py --all --json

# 5. Pacotes sociais (autoPublish: false)
python tools/publish_pack.py --all

# 6. Calendário editorial e matriz UTM (proposta; nada publica)
python tools/campaign_calendar.py --start-date 2026-11-23 --json

# 7. Portal de revisão humana (build determinístico + servidor local)
python tools/review_dashboard.py --build --json
python tools/review_dashboard.py --serve --port 8765

# 8. Auditoria de prontidão (qualquer estação/CI; avisos não reprovam)
python tools/release_audit.py --json

# 9. Gate de release (7 domínios; avisos também reprovam)
python tools/release_audit.py --strict --json

# 10. Consolidar o registro de sessões no contexto do projeto (idempotente)
python tools/devlog_sync.py --json
```

Para cadastrar um 5º nicho/tenant, siga [docs/guia-novo-nicho.md](guia-novo-nicho.md) (estrutura, schemas, fixture, campanha, validação e render em menos de 10 minutos).

## 5. Testes e CI

Suíte consolidada da fábrica — **16 módulos** (6 do núcleo de render, 3 da Etapa 2, 3 da Etapa 3 e 4 da Etapa 4), executada no CI (`.github/workflows/local-render-validation.yml`, etapa "Validar contratos multi-tenant e suites da fabrica (Etapas 2, 3 e 4)") em `ubuntu-latest` e `windows-latest`:

```bash
python -m unittest \
  tools/tests/test_render_local.py tools/tests/test_render_pipeline.py \
  tools/tests/test_build_video.py tools/tests/test_multi_format.py \
  tools/tests/test_srt_validate.py tools/tests/test_delivery_verify.py \
  tools/tests/test_tenant_contracts.py tools/tests/test_preset_runner.py \
  tools/tests/test_factory_cli.py tools/tests/test_audio_tts.py \
  tools/tests/test_publish_pack.py tools/tests/test_devlog_sync.py \
  tools/tests/test_derivative_formats.py tools/tests/test_review_dashboard.py \
  tools/tests/test_campaign_calendar.py tools/tests/test_release_audit.py -v
python tools/release_audit.py --strict --json
```

- `test_release_audit.py` (22 testes) cobre o contrato `schemaVersion 2` dos 7 domínios no repositório real, o sandbox que aprova no modo normal e reprova no `--strict` (matriz UTM ausente), o sandbox completo que aprova **7/7 no `--strict`**, e defeitos simulados por domínio: hash corrompido, storyboard/diretório de entrega/pacote/arquivo social ausentes, política de áudio violada nos dois sentidos, `autoPublish: true` e `guardrailsAudited: false`, contagem de slots divergente, declaração de derivado incompleta e derivado com hash divergente, caminho absoluto vazado no portal, artefatos da Etapa 4 ausentes (aviso, não falha), mídia rastreada, `.gitattributes` sem `eol=lf` e sem cobertura por extensão, worktree órfã e worktree registrada sem diretório, além de `--json`/`--report-out`/`PATH_OUTSIDE_ROOT` e da saída UTF-8 do CLI.
- `test_devlog_sync.py` (7 testes) cobre a consolidação da Etapa 3 (retrocompatibilidade byte a byte), a ordenação multi-etapa por `(etapa, agente)`, a atualização da linha `Fase atual`, a idempotência de execuções repetidas e o filtro `--pattern`.
- O CI também dispara com alterações em `05-review-portal/**`, `04-legendas/calendario-editorial.*`, `04-legendas/matriz-utm-consolidada.csv` e `docs/**`.
- **Dependência de consolidação:** o gate `--strict` exige 7/7 domínios. Enquanto `04-legendas/matriz-utm-consolidada.csv` (Agente 3) não estiver na main, o domínio 5 reporta o aviso `MATRIZ_UTM_AUSENTE` e o modo estrito reprova — no estado atual desta branch, `--json` retorna `ok: true` com 6 domínios ok e 1 aviso, e `--strict` retorna exit 1. Se for preciso manter o CI verde antes dessa consolidação, remova `--strict` dessa linha; a auditoria continua honesta nos dois modos.

## 6. Referências

- [docs/guia-novo-nicho.md](guia-novo-nicho.md) — cadastrar um novo projeto/nicho em menos de 10 minutos.
- [docs/contexto/README.md](contexto/README.md) — estado atual, próximos passos e handoff.
- [WORKFLOW.md](../WORKFLOW.md) — fluxo editorial completo e regra de vídeo sem áudio.
- [AGENTS.md](../AGENTS.md) — regras do projeto, portabilidade entre estações e uso de `.workspace/`.
- [platform/README.md](../platform/README.md) — núcleo reutilizável (Studio, perfis de saída, provas HTTP).

