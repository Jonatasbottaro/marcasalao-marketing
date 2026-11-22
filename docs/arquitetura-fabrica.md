# Arquitetura da Fábrica de Vídeo Multi-Tenant

Documento mestre do pipeline de produção de vídeo programático multi-tenant (Etapas 2 a 6). Público: operadores e agentes que executam, estendem ou auditam a fábrica. A fonte da verdade é o código; este documento descreve o comportamento comprovado pelos testes e pelo CI. O fluxo para o titular está resumido em [docs/guia-operacional-titular.md](guia-operacional-titular.md).

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

Etapa 5/5B (camada de acabamento, transversal):
    bootstrap_ffmpeg ──> factory_cli pipeline ──> static_cards ──> utm_simulator
                              │                                          │
                              └────────────> editorial_qa ──> handoff_bundler (pós-aprovação)

Etapa 6 (operação do titular):
    review_dashboard --serve / approval_cli ──> factory_cli handoff ──> publicação MANUAL
                         │                                               │
                         └──> utm_report_importer ──> workspace_doctor ───┘ (fechamento semanal)

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

Os 5 tenants atuais (14 campanhas, calendário de 7 semanas / 56 slots):

| Tenant | Marca | Preset | Domínio | Faixa de áudio | Campanhas |
| --- | --- | --- | --- | --- | --- |
| `marca-salao` | Marca Salão | `saas-demo` | marcasalao.com.br | Proibida (`-an`, narração externa obrigatória) | 3 |
| `multitrack-hub` | Multitrack Hub | `shorts-completo` | multitrackhub.com.br | Permitida (trilha opcional via `audio_tts`) | 5 |
| `meu-salao` | Meu Salão | `saas-demo` | meusalao.com.br | Proibida | 4 |
| `estudio-flow` | Estúdio Flow | `saas-demo` | estudioflow.com.br | Proibida | 3 |
| `clinica-vital` | Clínica Vital | `saas-demo` | clinicavital.com.br | Proibida | 4 |

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
- `pipeline [--all | --tenant <id> [--campaign <slug>]] [--skip-render] [--start-date YYYY-MM-DD] [--weeks N] [--strict-audit] --json` (Etapa 5B) — subcomando mestre end-to-end: encadeia contratos → render 9:16 → derivados → cards estáticos → pacotes sociais → calendário → portal → auditoria UTM → Release Gate. Os módulos paralelos são importados de forma opcional: se um ainda não existir, o estágio é marcado `skipped` e o restante continua. Com `--skip-render`, os estágios de produção apenas verificam os artefatos versionados existentes.
- `handoff --all-approved [--json]` (Etapa 6) — subcomando de operação diária: empacota **somente** campanhas aprovadas pelo titular, reauditando a copy contra os guardrails e gravando `autoPublish: false`. Equivale ao fluxo do `handoff_bundler.py`, integrado na CLI mestre; com nenhuma aprovação, não gera pacote e reporta o motivo. Ver [guia operacional](guia-operacional-titular.md).

### 2.7 `tools/publish_pack.py` — pacotes sociais (Agente 3, Etapa 3)

Lê a entrega renderizada + brand-kit (domínio, UTMs) + guardrails e gera os textos por rede (`instagram-reels.md`, `youtube-shorts.md`, `facebook-reels.md`) e o `checklist-publicacao.json` com `autoPublish: false`. Todas as legendas são auditadas contra `forbiddenClaims`/`forbiddenUiElements` antes de gravar; texto proibido aborta o pacote sem gravar parcial. CLI: `python tools/publish_pack.py --all` ou `--tenant <id> --slug <slug>`.

> **Efeito colateral conhecido:** re-executar `publish_pack` (ou sua suíte de testes) numa estação **sem** os `.mp4` em disco re-verifica e regrava `sha256_disk_ok: false` nos checklists versionados. Restaure com `git checkout -- 04-legendas/` nesses casos; o valor `true` reflete a estação que renderizou. O `release_audit` trata vídeo ausente como **aviso**, não falha.

### 2.8 `tools/release_audit.py` — gate de release em 8 domínios (Agente 4, Etapa 4)

Auditor final de prontidão em uma passada (`python tools/release_audit.py [--strict] [--json] [--report-out <arquivo>] [--root <raiz>]`; API `run_release_audit(root, strict=False) -> dict`, relatório `schemaVersion: 2` com `domains[]` e `summary`). Cada problema carrega `severity` (`error` | `warning`), `code` e `message`; `error` reprova sempre, `warning` só reprova com `--strict`.

| # | Domínio (`id`) | O que verifica | Erros típicos |
| --- | --- | --- | --- |
| 1 | `contratos_tenants` | ≥ 4 tenants válidos via `tenant_validator` (brand-kit, guardrails, fixture; `strict=False`, agregando erros) | `TENANT_INVALIDO`, `TENANTS_INSUFICIENTES` |
| 2 | `entregas_video` | Por campanha: diretório, `manifest.json`, `<slug>.srt`, `<slug>_narracao.txt`, `preview-storyboard.png` com SHA-256 e bytes conferidos em disco; política de áudio simétrica (`allowAudioTrack: false` ⇒ `ffprobe.audioStreams == 0`; `true` ⇒ `>= 1`) | `DELIVERY_DIR_AUSENTE`, `MANIFEST_AUSENTE`, `HASH_DIVERGENTE`, `TAMANHO_DIVERGENTE`, `ARQUIVO_AUSENTE`, `POLITICA_AUDIO_DESCUMPRIDA` |
| 3 | `pacotes_sociais` | `checklist-publicacao.json` com `autoPublish: false` e `guardrailsAudited: true`, os três textos por rede e o SHA-256 das mídias declaradas | `PACOTE_AUSENTE`, `AUTO_PUBLICACAO_ATIVO`, `GUARDRAILS_NAO_AUDITADOS`, `ARQUIVO_PACOTE_AUSENTE` |
| 4 | `derivados_multiformato` | `derivatives.json` por campanha com as três declarações (`cover`, `1x1`, `16x9`) e hash; derivado presente em disco tem SHA-256 conferido | `DERIVADO_DECLARACAO_AUSENTE`, `DERIVADO_SEM_HASH`, `HASH_DIVERGENTE` |
| 5 | `calendario_utm` | `calendario-editorial.json` (estrutura, `totalSlots` == `len(slots)`, `autoPublish: false` no topo e em cada slot), `.md` e `matriz-utm-consolidada.csv` | `CALENDARIO_INVALIDO`, `SLOTS_CONTAGEM_DIVERGENTE`, `AUTO_PUBLICACAO_ATIVO` |
| 6 | `portal_revisao` | `05-review-portal/` com `index.html`, `portal-data.json`, `README.md`; varredura de caminhos absolutos de estação vazados no JSON/HTML | `CAMINHO_ABSOLUTO_VAZADO` |
| 7 | `higiene_git` | `git ls-files "*.mp4" "*.wav"` vazio; `.gitattributes` com regra `eol=lf` cobrindo `.json`, `.srt`, `.md` e `.html`; worktrees históricas (`prova-campanha-conclusao`, `studio-package-verify2`) preservadas | `MIDIA_RASTREADA`, `GITATTRIBUTES_SEM_EOL_LF`, `GITATTRIBUTES_EXT_SEM_EOL_LF`, `WORKTREE_REGISTRADA_SEM_DIRETORIO` |

Avisos (`warning`, não reprovam no modo normal; **reprovam com `--strict`**): `DERIVATIVES_AUSENTE`, `CALENDARIO_AUSENTE`, `MATRIZ_UTM_AUSENTE`, `PORTAL_ARQUIVO_AUSENTE` e `WORKTREE_ORFA` — ou seja, artefatos de consolidação ainda ausentes e worktree histórica com diretório sem registro.

**Mídia local da estação não é defeito:** o `<slug>.mp4` da entrega e os derivados sob `.workspace/archives/<slug>/derivatives/` não são versionados; quando ausentes em disco não geram problema (o manifesto e a declaração preservam hash, ffprobe e comando reproduzível), e quando presentes têm o SHA-256 conferido. Por isso o modo normal roda em qualquer estação ou checkout novo do CI, e o `--strict` só exige o que está declarado no Git.

`--report-out <arquivo>` grava o relatório JSON (UTF-8, LF) em caminho obrigatoriamente contido sob a raiz; caminho externo é recusado com `PATH_OUTSIDE_ROOT`. A saída do CLI é UTF-8 mesmo no Windows, onde o encoding padrão de pipe é o da locale.

Exit codes: `0` aprovado; `1` reprovado; `2` erro de uso/execução.

### 2.8.1 Domínio 8 — `empacotamento_distribuicao` (Agente 1, Etapa 11)

O `release_audit` inclui um oitavo domínio que varre `.workspace/bundles/<tenantId>/<slug>/` e, para cada `.zip` encontrado, executa `publish_bundler.verify_bundle()`. Quando não há bundles na estação, o domínio emite um aviso (`BUNDLES_AUSENTES`) — não reprova no modo normal, mas reprova com `--strict`. Problemas de hash divergente, manifesto ausente, entrada faltando ou entradas desordenadas aparecem como erros.

### 2.9 `tools/publish_bundler.py` — empacotamento determinístico de distribuição (Agente 1, Etapa 11)

Consolida artefatos aprovados de uma campanha em pacotes `.zip` portáveis e auditáveis por SHA-256, sem violar políticas de versionamento nem publicação manual. Cada pacote pertence a um único `tenant_id` e grava em ``.workspace/bundles/<tenantId>/<slug>/`` (não rastreado pelo Git).

O ZIP é bit-determinístico: entradas ordenadas lexicograficamente, data/hora fixa no `ZipInfo`, permissões normalizadas (`0o600`), JSON em UTF-8 com LF (`\n`). O campo `autoPublish` é sempre `false`.

CLI (a partir da raiz do checkout):
    python tools/publish_bundler.py pack --tenant <id> --slug <slug>
        [--allow-unapproved] [--json] [--root <raiz>]
    python tools/publish_bundler.py verify --bundle <caminho.zip> [--json]
        [--root <raiz>]
    python tools/publish_bundler.py verify --all [--json] [--root <raiz>]
        # verifica todos os bundles de .workspace/bundles/ (padrao sem --bundle);
        # estacao sem bundles e' ok (checkedCount 0); e' o modo usado pelo gate 7
        # do release_check

API: `pack_bundle(root, tenant_id, slug, allow_unapproved=False) -> dict` e
`verify_bundle(bundle_path, root=".") -> dict`; exceção `PublishBundlerError`.

O `pack_bundle` falha fechada: exige decisão `aprovado` em
`.workspace/tmp/aprovacoes-titular.json` a menos que `--allow-unapproved` (selo
`PREVIA_NAO_APROVADA`); decisões `ajuste` nunca entram (`SLOT_EM_AJUSTE`). Antes de
gravar o ZIP, confere o SHA-256 de masters e derivados em `.workspace/archives/`
contra o manifesto e o `derivatives.json`. Grava, ao lado do ZIP, um
`<slug>-v<SCHEMA_VERSION>-manifest.json` com `schemaVersion`, `tenantId`,
`brandName`, `domain`, `slug`, `autoPublish: false`, `approvalStatus`,
`audioPolicy`, `bundlePath`, `bundleSha256`, `bundleBytes`, `promotionHistory[]`,
`items[]` e `bundleSummary`.

`verify_bundle` recalcula o SHA-256 do ZIP, confere o manifesto, valida que cada
item declarado existe no ZIP com o mesmo hash, e confirma que as entradas do ZIP
estão ordenadas lexicograficamente. Qualquer divergência reprova com `ok: false`.

### 2.10 `tools/devlog_sync.py` — registro de sessões (Agente 4, Etapa 4)

Consolida devlogs `.workspace/devlogs/etapa*-agente*.md` no `contexto_projeto.md` (Seção 1 "Estado atual" + Seção 7 "Histórico de sessões"), com ordenação numérica por `(etapa, agente)`, idempotência por marcador `<!-- devlog-sync:<arquivo> -->` e retrocompatibilidade total com os registros da Etapa 3. `--pattern` restringe a descoberta (padrão `etapa*-agente*.md`); o resultado JSON reporta `pattern` e a etapa/agente de cada entrada. A consolidação é idempotente: re-execuções não duplicam entradas já aplicadas. CLI: `python tools/devlog_sync.py [--pattern <glob>] [--json]`.

### 2.11 `tools/derivative_formats.py` — derivados multiformato (Agente 1, Etapa 4)

Parte dos MP4s verticais arquivados em `.workspace/archives/<slug>/<slug>.mp4` (mais o `manifest.json` da entrega e o brand-kit do tenant) e gera, por campanha, em `.workspace/archives/<slug>/derivatives/`:

- `<slug>-cover.png` — frame representativo (segundo 2.0, ou metade da duração em fontes mais curtas) em 1080×1920, com moldura sutil na cor primária do brand-kit.
- `<slug>-1x1.mp4` — 1080×1080@30 H.264/yuv420p, com fundo desfocado e escurecido derivado do próprio vídeo e o 9:16 centralizado.
- `<slug>-16x9.mp4` — 1920×1080@30, mesma composição.

Grava também `derivatives.json` **na entrega versionada** (`02-reels-shorts/deliveries/<tenant>/<slug>/`), declarando `source` (caminho, SHA-256, ffprobe) e os cinco derivados do manifesto v2 (`1x1`, `16x9`, `cover`, `thumb-16x9`, `preview-formats`) com caminho, SHA-256, bytes e comando reproduzível — o domínio 4 do `release_audit` exige as declarações `cover`, `1x1` e `16x9`. CLI: `python tools/derivative_formats.py (--all | --tenant <id> [--campaign <slug>]) [--json]`. Como os MP4s de origem são locais da estação, a geração exige a estação que renderizou; a declaração versionada preserva a integridade para as demais.

### 2.12 `tools/campaign_calendar.py` — calendário editorial e matriz UTM (Agente 3, Etapa 4)

Lê os tenants validados e os `checklist-publicacao.json` gerados pelo `publish_pack` e distribui as campanhas num cronograma intercalado: até 2 campanhas por dia, nunca duas do mesmo tenant no mesmo dia (seleção gulosa pelos tenants com mais campanhas restantes), cada campanha cobrindo os 3 canais configurados (Instagram Reels, YouTube Shorts, Facebook Reels) em suas janelas horárias. Todos os slots nascem com `autoPublish: false` e `statusEditorial: "aguardando_aprovacao_titular"` — o calendário é proposta, nunca publicação.

Saídas: `04-legendas/calendario-editorial.json` (estrutura completa dos slots, com `audioPolicy`, `utmUrl` e contagens) e `04-legendas/calendario-editorial.md` (cronograma cronológico, checklist e matriz consolidada das URLs UTM). CLI: `python tools/campaign_calendar.py --start-date YYYY-MM-DD [--json]`.

> **Consolidação concluída:** o arquivo separado `04-legendas/matriz-utm-consolidada.csv`, esperado pelo domínio 5 do `release_audit`, já consta no repositório. Com ele presente, o domínio 5 não reporta `MATRIZ_UTM_AUSENTE`. O domínio 8 (`empacotamento_distribuicao`) emite um aviso (`BUNDLES_AUSENTES`) quando não há bundles na estação — não reprova no modo normal, mas reprova com `--strict`.

### 2.13 `tools/review_dashboard.py` — portal de revisão humana (Agente 2, Etapa 4)

Consolida tenants (brand-kit + guardrails), entregas (manifesto, SRT, narração, storyboard) e pacotes sociais (checklist + os três textos por rede) num portal estático em `05-review-portal/`: `index.html` (dados embutidos, abre direto via `file://`), `portal-data.json` e `README.md`. O build é determinístico — não grava timestamps e produz bytes idênticos para os mesmos insumos, de modo que o portal versionado é o mesmo em qualquer estação.

CLI: `python tools/review_dashboard.py --build [--json]` para gerar e `python tools/review_dashboard.py --serve [--port 8765]` para revisar no navegador. O portal é somente leitura: nenhuma ação dele publica, agenda ou altera artefato. O domínio 6 do `release_audit` exige os três arquivos e varre o JSON/HTML em busca de caminhos absolutos de estação vazados (`CAMINHO_ABSOLUTO_VAZADO`).

### 2.14 `tools/bootstrap_ffmpeg.py` — bootstrap portátil de FFmpeg (Agente 1, Etapa 5B)

Instala de forma idempotente o pacote essencial do Windows (gyan.dev) em `<MAIN_ROOT>/.workspace/tools/ffmpeg/` e valida `ffmpeg`/`ffprobe` com `-version`. `MAIN_ROOT` é resolvido por `git rev-parse --git-common-dir`, de modo que a instalação fica no checkout principal e é compartilhada por todas as worktrees. 100% stdlib; nenhum `.exe`/`.zip` é versionado. CLI: `python tools/bootstrap_ffmpeg.py [--check-only] [--force] [--json]`; API: `ensure_ffmpeg_tools(root=".", force=False) -> dict`.

### 2.15 `tools/static_cards.py` — cards estáticos de Stories e Carrossel (Agente 1, Etapa 5)

Gera, por campanha, dois kits versionados em `01-insta-stories/deliveries/<tenant>/<slug>/`: `stories/` (3 banners 1080×1920) e `carousel/` (4 slides 1080×1350), mais `static-manifest.json` (schemaVersion 1, `guardrailsAudited`, dimensões, bytes e SHA-256 das 7 lâminas). Usa as mesmas primitivas PNG bitmap 5×7 de `tools/ns002_pilot.py`, sem Pillow, e auditoriza todos os textos contra guardrails **antes** de renderizar qualquer pixel. CLI: `python tools/static_cards.py (--all | --tenant <id> [--campaign <slug>]) [--types stories,carousel] --json`. Não produz áudio.

### 2.15 `tools/handoff_bundler.py` — empacotamento diário pós-aprovação (Agente 2, Etapa 5B)

Cruza as aprovações do titular (`aprovacoes-titular.json`, schemas v1/v2 do `review_dashboard`), o calendário editorial, os pacotes sociais e os derivados para montar, em `.workspace/handoff-diario/<data>/<slotId>-<tenant>-<canal>/`, a ficha `POSTAGEM-MANUAL.md`, o `copy-pronta.txt`, o `handoff-manifest.json` (com `autoPublish: false`, hashes e status da mídia local) e a mídia correspondente quando presente no arquivo. Falha fechada: sem `--include-pending` empacota somente campanhas explicitamente aprovadas; decisão `ajuste` nunca entra; a copy é reauditada contra os guardrails. CLI: `python tools/handoff_bundler.py --all-approved [--json]` ou `--date YYYY-MM-DD [--include-pending]`. Nada é publicado.

### 2.16 `tools/utm_simulator.py` — auditoria e simulação de funil UTM (Agente 4, Etapa 5B)

Audita 100% das URLs UTM do `calendario-editorial.json` (e deriva a URL padrão do brand-kit para campanhas ainda não agendadas): HTTPS, host igual ao `domain`, presença e alfabeto de `utm_source`/`utm_medium`/`utm_campaign`/`utm_content`, `utm_campaign` igual ao slug e ausência de colisão de atribuição entre tenants. Com `--simulate-traffic`, gera sessões sintéticas determinísticas (seed fixa) das duas ondas e um catálogo de eventos de conversão por nicho, sem nenhum campo monetário preenchido. CLI: `python tools/utm_simulator.py [--calendar <arquivo>] [--simulate-traffic] [--out-dir .workspace/tmp/utm-sim] [--seed N] --json`.

### 2.17 `tools/editorial_qa.py` — auditoria editorial transversal (Agente 8, Etapa 5B)

Audita todas as campanhas descobertas em `tenants/*/campaigns/*.json` (14 campanhas, 7 lentes independentes), 100% stdlib e somente leitura:

| Lente (`id`) | O que verifica | Código típico |
| --- | --- | --- |
| `duracao_srt_manifest` | Fim do último cue do SRT igual a `format.duration` do manifesto (padrão 30.0 s, tolerância 1 ms) e validade estrutural do SRT via `srt_validate` | `SRT_DURACAO_DIVERGENTE`, `SRT_SEM_CUES` |
| `legibilidade_mobile` | Nenhuma linha de cue com mais de 48 caracteres; nenhum bloco vazio | `SRT_LINHA_LONGA` (aviso), `SRT_BLOCO_VAZIO` (erro) |
| `paridade_entregas` | Presença e identidade (`tenantId`/`slug`) entre vídeo, cards estáticos (quando presentes) e pacote social | `PACOTE_SOCIAL_AUSENTE`, `CARDS_ESTATICOS_AUSENTE` (aviso), `PARIDADE_SLUG_DIVERGENTE` |
| `guardrails_cruzados` | Re-auditoria de `forbiddenClaims`/`forbiddenUiElements` em SRT, narração e três legendas sociais | `GUARDRAIL_VIOLACAO` |
| `integridade_utf8` | Ausência de U+FFFD e de sequências de mojibake em todos os arquivos UTF-8 auditados | `MOJIBAKE_DETECTADO`, `UTF8_INVALIDO` |
| `coerencia_hooks_calendario` | Quando há `calendario-editorial.json`, cada campanha agendada tem `hookVarianteA`/`hookVarianteB` não vazios, distintos e livres de violações de guardrails | `HOOK_VARIANTE_AUSENTE` (erro), `HOOK_VARIANTE_IDENTICA` (aviso) |
| `aderencia_ui_labels` | Quando `brand-kit.json` define `uiLabels`, todos os valores são strings não vazias e passam em `validate_text_against_guardrails` com UI elements habilitados | `UI_LABEL_INVALIDO` |

`error` reprova sempre; `warning` reprova somente com `--strict` (é o caso das linhas de SRT acima de 48 caracteres, ainda presentes no acervo atual). CLI: `python tools/editorial_qa.py [--all | --tenant <id>] [--strict] [--json]`; API: `run_editorial_qa(root=".", strict=False, tenant=None) -> dict`, relatório `schemaVersion: 1` com `campaigns[]`, `checks[]` e `summary`. Exit codes: 0 aprovado, 1 reprovado, 2 erro de uso.

### 2.18 Camada de operação do titular (Etapa 6)

Fecha o ciclo entre a aprovação humana, a publicação manual e o aprendizado semanal. O passo a passo completo está em [docs/guia-operacional-titular.md](guia-operacional-titular.md); a rotina de métricas está no [playbook de UTM](analytics-utm-playbook.md).

| Módulo / contrato | Papel na operação | Ponto de entrada |
| --- | --- | --- |
| `tools/srt_formatter.py` | Normalização/quebra de linha das legendas para legibilidade mobile (limite de 48 caracteres por linha do `editorial_qa`), sem alterar timecodes nem duração final | CLI em `tools/srt_formatter.py` |
| `tools/approval_cli.py` | Leitura e registro das decisões do titular no mesmo arquivo `aprovacoes-titular.json` (schema v2) usado pelo portal: `aguardando` / `aprovado` / `ajuste` e conferência de locução externa | `python tools/approval_cli.py status` · `python tools/approval_cli.py decide ...` |
| `tools/factory_cli.py handoff` | Empacotamento diário pós-aprovação: ficha `POSTAGEM-MANUAL.md`, `copy-pronta.txt`, `handoff-manifest.json` e mídia local, com `autoPublish: false` | `python tools/factory_cli.py handoff --all-approved --json` |
| `tools/utm_report_importer.py` | Importação/reconciliação do relatório exportado da ferramenta de analytics contra `04-legendas/matriz-utm-consolidada.csv`, na chave `(tenant_id, slug, utm_source, utm_medium, utm_content)`, e reconciliação bundle → UTM (`bundleAttribution`) conectando manifestos de `.workspace/bundles/` aos slots de desempenho | `python tools/utm_report_importer.py --json` · `python tools/utm_report_importer.py --reconcile-bundles --json` |
| `tools/workspace_doctor.py` | Diagnóstico de saúde do checkout antes do próximo ciclo (estrutura, contratos, artefatos, portabilidade e consistência local) | `python tools/workspace_doctor.py --check` |
| `uiLabels` no `tenants/<tenantId>/brand-kit.json` | Rótulos de interface exibidos no portal e no handoff (decisões, locução externa, chamadas por rede), substituindo textos fixos por termos configuráveis por marca | objeto `uiLabels` no brand-kit; requer `additionalProperties` do schema actualizado na consolidação |
| `docs/guia-operacional-titular.md` | Manual único da rotina diária (revisão → handoff → publicação manual) e semanal (métricas UTM + doctor) | documento versionado em `docs/` |

**Estado de consolidação:** estes módulos são desenvolvidos em paralelo por outros agentes da Etapa 6. No commit em que esta seção foi escrita, ainda não constavam na `main`; as interfaces acima seguem o contrato do pedido e devem ser reconferidas contra o código e o `--help` de cada ferramenta na integração. Nenhuma delas publica, agenda ou cria rascunho, e nenhuma gera áudio.

### 2.19 Resiliência da suíte, auto-reparo de mídia e relatório executivo (Etapa 13)

Três frentes integradas que fecham o ciclo semanal sem ampliar a superfície de publicação.

| Módulo / contrato | Papel na operação | Ponto de entrada |
| --- | --- | --- |
| `tools/run_tests.py` | Runner determinístico da suíte Python em quatro faixas mutuamente exclusivas: `smoke` (loop de dev), `fast` (unitários e de contrato, sem render — gate oficial), `render` (FFmpeg/FFprobe reais) e `all` (fast + render). A partição é fechada: módulo `test_*.py` novo sem classificação reprova com erro de uso. Toda execução roda sob blindagem de `.workspace/archives/` | `python tools/run_tests.py --smoke --json` · `--fast` · `--render` · `--all` |
| `tools/archives_guard.py` | `ArchivesGuard` fotografa os SHA-256 dos masters antes do run e restaura qualquer arquivo alterado/removido ao final, descartando mídia nova criada pelo teste. `isolated_archives()` fornece `archives_dir` descartável. Temporários sempre sob `<RAIZ>/.workspace/tmp/` | `ArchivesGuard(root)` · `isolated_archives(root)` |
| `tools/workspace_doctor.py --repair` | Reparo cirúrgico de mídia local por slot. Dry-run por padrão (`--dry-run` explicita); `--apply` grava. Restaura o master da cópia versionada intacta quando o SHA-256 confere, ou re-renderiza o slot em staging isolado pelo pipeline canônico, promovendo só após validar SHA-256 + ffprobe. Derivados são regenerados apenas com master íntegro | `python tools/workspace_doctor.py --repair [--dry-run \| --apply] [--slug S] [--tenant T] [--json]` |
| `tools/executive_summary.py` | Relatório executivo semanal por tenant, somente leitura, reutilizando `editorial_qa` (por tenant, com filtro nativo), `approval_cli`, `campaign_calendar`, `utm_report_importer` e `publish_bundler` sem duplicar fórmulas. Gera JSON + Markdown em `.workspace/reports/<tenantId>/` | `python tools/executive_summary.py (--tenant <id> \| --all) [--week 1..7] [--json]` · API `build_executive_summary(root, tenant_id, week=None, inputs=None)` |
| `tools/release_check.py` (gate 8) | Gate da suíte particionada: `run_tests.py --fast` por padrão; `--smoke-tests` troca para `--smoke` (pré-commit local) e `--full-tests` para `--all` (fast + render). As duas flags são mutuamente exclusivas | `python tools/release_check.py [--smoke-tests \| --full-tests]` |
| `executiveSummary` em `portal-data.json` | Digest por tenant no portal de revisão: indicadores-chave e caminho/status (`gerado` / `ausente`) do relatório. O portal apenas lê os relatórios já gerados | painel `#resumo-executivo` em `05-review-portal/index.html` |
| **Etapa 14 — onboarding automatizado de tenants e planejador de capacidade** (estań atual) | | |
| `tools/tenant_scaffolder.py` | Onboarding automatizado: gera brand-kit.json, guardrails.json, fixture editorial e campanha inicial com validação de guardrails e editorial QA. CLI com flags `--dry-run`/`-apply`, `--tenant-id`, `--brand-name`, `--domain`, `--audio-policy`, `--with-campaign`, `--campaign-title`. API `scaffold_tenant(tenant_id, brand_name, domain, audio_policy, tagline, palette, with_campaign, campaign_title, root, apply)`. | `python tools/tenant_scaffolder.py --tenant-id X --brand-name "Y" --domain Z --dry-run` · API `scaffold_tenant(...)` |
| `tools/campaign_calendar.py --simulate-capacity` | Planejador de capacidade editorial: simula impacto de novos tenants/campanhas no horizonte atual sem gravar nada. Retorna current/threshold/simulated/weekDelta. CLI com flags `--simulate-capacity`, `--extra-campaigns N`, `--extra-tenants N`, `--start-date YYYY-MM-DD`. | `python tools/campaign_calendar.py --simulate-capacity --extra-campaigns 3 --json` |
| `tools/executive_summary.py --capacityStatus` | Inclui bloco `capacityStatus` no relatório executivo com campanhasAtivas, semanasMinimas, espacoLivreNoHorizonteAtual via campaign_calendar.simulate_calendar_capacity(root). | `python tools/executive_summary.py --tenant X --json` |

**Blindagem de `.workspace/archives/`.** Dois testes de render chamavam o pipeline canônico sem `archives_dir` isolado e sobrescreviam os masters reais (`test_audio_tts.py` com bed de áudio externo e `test_factory_cli.py` via `factory_cli render`). `factory_cli.cmd_render` e `cmd_pipeline` passaram a aceitar `archives_dir` / `--archives-dir`; os dois testes usam diretório isolado e instalam `ArchivesGuard` em `setUpModule`, de modo que a proteção vale tanto via `run_tests.py` quanto por `unittest` direto.

**Limites do reparo.** O reparo é local e não re-declara manifestos versionados. Quando a cópia versionada está intacta, a restauração é byte-exata. Quando não está, o slot é re-renderizado em staging e só é promovido se o SHA-256 produzido for igual ao declarado; caso contrário o item é reportado como `MASTER_NAO_REPRODUTIVEL` e nada é gravado (fail-closed). Insumo ausente → `INSUMO_AUSENTE`; divergência de ffprobe após o reparo → `FFPROBE_DIVERGENTE_POS_REPARO`. O relatório traz `dryRun`, `plannedItems`, `repairedItems`, `skippedItems`, `remainingErrors` e `ok`.

**Pipeline canônico do master.** O re-render usa `preset_runner.run_preset_pipeline`, não `render_local.run_render`: este último consome um `CreativeExecutionPackage` e emite `delivery-manifest.json`, sem nunca escrever `manifest.json` nem `.workspace/archives/`. É o `preset_runner` que grava o par manifesto + MP4 de arquivo (o campo `command` dos manifestos versionados registra exatamente essa invocação). Não existe `tools/batch_render.py` no repositório; o equivalente em lote é `factory_cli.cmd_render`, que o reparo evita por não isolar archives por slot.

**Ausência de dados é explícita.** Sem relatório UTM ou sem bundles na estação, as seções de A/B, fadiga e atribuição declaram `sem dados` com o motivo, em vez de recalcular estatística. O relatório nunca publica, agenda, aprova ou altera datas, canais e UTMs; `autoPublish: false` aparece no JSON e no Markdown. A governança expõe `tenantId`, `brandName`, `generatedAt` (UTC ISO-8601) e `weekFilter`.

**Armadilha de unidade no benchmark.** `rankings.tenantBenchmarks.byTenant[].abWinRatePct` é gravado pelo importer como **fração 0..1** (`round(wins/total, 4)`), apesar do sufixo `Pct`. O relatório expõe `benchmarkAbWinRate` com `fraction` e `percent` lado a lado, e lê a fadiga do benchmark pelos campos `hooksComFadiga*` (distintos dos `fatigue*` dos slots do calendário).

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

# 1. Validar contratos (5 tenants)
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

# 8. Cards estáticos: stories 1080x1920 + carrossel 1080x1350 (Etapa 5)
python tools/static_cards.py --all --json

# 9. Auditoria de URLs UTM (Etapa 5B; --simulate-traffic opcional)
python tools/utm_simulator.py --json

# 10. Auditoria editorial transversal (5 lentes; --strict também reprova avisos)
python tools/editorial_qa.py --all --json
python tools/editorial_qa.py --all --strict --json

# 11. Bootstrap portátil de FFmpeg (somente se a estação não tiver os binários)
python tools/bootstrap_ffmpeg.py --check-only --json

# 12. Handoff diário pós-aprovação (somente campanhas aprovadas pelo titular)
python tools/handoff_bundler.py --all-approved --json

# 13. Pipeline mestre end-to-end (opcional; verifica artefatos com --skip-render)
python tools/factory_cli.py pipeline --all --skip-render --json

# 14. Auditoria de prontidão (qualquer estação/CI; avisos não reprovam)
python tools/release_audit.py --json

# 14a. Gate único de release: orquestra higiene Git, TS, contratos, editorial,
#      workspace_doctor, release_audit --strict, suíte particionada e E2E
python tools/release_check.py
python tools/release_check.py --skip-ts     # quando platform/ já foi compilado
python tools/release_check.py --json        # relatório JSON no stdout
python tools/release_check.py --full-tests  # gate de testes com fast + render
python tools/release_check.py --smoke-tests # gate de testes rapido (pre-commit local)

# 15. Gate de release (7 domínios; avisos também reprovam)
python tools/release_audit.py --strict --json

# 16. Consolidar o registro de sessões no contexto do projeto (idempotente)
python tools/devlog_sync.py --json

# 17. Revisão humana (Etapa 6): portal local ou CLI de aprovações
python tools/review_dashboard.py --serve --port 8765
python tools/approval_cli.py status
#   (decisão no portal ou via approval_cli decide; -an exige locução externa conferida)

# 18. Pacote diário de postagem manual (somente aprovados)
python tools/factory_cli.py handoff --all-approved --json
#   -> .workspace/handoff-diario/<data>/<slot>/ ; publicação é MANUAL

# 19. Normalizar legendas para legibilidade mobile quando necessário (Etapa 6)
python tools/srt_formatter.py --help

# 20. Fechamento semanal: importar métricas UTM e checar o workspace
python tools/utm_report_importer.py --json
python tools/utm_report_importer.py --reconcile-bundles --json
python tools/workspace_doctor.py --check

# 21. Reparo cirúrgico de mídia local quando houver divergência de SHA-256
python tools/workspace_doctor.py --repair --json          # dry-run: só o plano
python tools/workspace_doctor.py --repair --apply --json  # executa e revalida
python tools/workspace_doctor.py --repair --apply --slug <slug> --json

# 22. Relatório executivo semanal por tenant (somente leitura)
python tools/executive_summary.py --all --json
python tools/executive_summary.py --tenant <id> --week 3
#   -> .workspace/reports/<tenantId>/relatorio-executivo-<tenantId>.{json,md}
#   o portal de revisão passa a exibir o digest por tenant

# 23. Suíte Python particionada (Etapa 13 / 13.1) — faixas mutuamente exclusivas
python tools/run_tests.py --smoke --json   # loop de dev: 24 modulos, sem contratos pesados
python tools/run_tests.py --fast --json    # gate oficial: 28 modulos, sem render
python tools/run_tests.py --render --json  # testes que usam FFmpeg/FFprobe
python tools/run_tests.py --all --json     # fast + render
```

Para cadastrar um novo nicho/tenant, siga [docs/guia-novo-nicho.md](guia-novo-nicho.md) (estrutura, schemas, fixture, campanha, validação e render em menos de 10 minutos).

## 5. Testes e CI

Suíte consolidada da fábrica — **21 módulos** (6 do núcleo de render, 3 da Etapa 2, 3 da Etapa 3, 4 da Etapa 4 e 5 da Etapa 5/5B), executada no CI (`.github/workflows/local-render-validation.yml`) em `ubuntu-latest` e `windows-latest`. O workflow roda, após compilar `platform/` (`npm run build && npm test`): (1) a verificação única `python tools/release_check.py --skip-ts --json`, que orquestra higiene Git + `autoPublish: false`, contratos (5 tenants), editorial `--all --strict` (14 campanhas/7 lentes), `workspace_doctor --check`, `release_audit --strict` (7/7 domínios) e a suíte E2E; e (2) a suíte `unittest` canônica da fábrica e o `discover -s tests/e2e`. Os módulos também são apanhados pela descoberta `python -m unittest discover -s tools/tests -v`:

```bash
python -m unittest \
  tools/tests/test_render_local.py tools/tests/test_render_pipeline.py \
  tools/tests/test_build_video.py tools/tests/test_multi_format.py \
  tools/tests/test_srt_validate.py tools/tests/test_delivery_verify.py \
  tools/tests/test_tenant_contracts.py tools/tests/test_preset_runner.py \
  tools/tests/test_factory_cli.py tools/tests/test_audio_tts.py \
  tools/tests/test_publish_pack.py tools/tests/test_devlog_sync.py \
  tools/tests/test_derivative_formats.py tools/tests/test_review_dashboard.py \
  tools/tests/test_campaign_calendar.py tools/tests/test_release_audit.py \
  tools/tests/test_bootstrap_ffmpeg.py tools/tests/test_static_cards.py \
  tools/tests/test_handoff_bundler.py tools/tests/test_utm_simulator.py \
  tools/tests/test_bundle_attribution.py tools/tests/test_editorial_qa.py -v
python tools/release_audit.py --strict --json
python tools/editorial_qa.py --all --json
```

- `test_release_audit.py` (22 testes) cobre o contrato `schemaVersion 2` dos 8 domínios no repositório real, o sandbox que aprova no modo normal e reprova no `--strict` (matriz UTM ausente), o sandbox completo que aprova no `--strict`, e defeitos simulados por domínio: hash corrompido, storyboard/diretório de entrega/pacote/arquivo social ausentes, política de áudio violada nos dois sentidos, `autoPublish: true` e `guardrailsAudited: false`, contagem de slots divergente, declaração de derivado incompleta e derivado com hash divergente, caminho absoluto vazado no portal, artefatos da Etapa 4 ausentes (aviso, não falha), mídia rastreada, `.gitattributes` sem `eol=lf` e sem cobertura por extensão, worktree órfã e worktree registrada sem diretório, além de `--json`/`--report-out`/`PATH_OUTSIDE_ROOT` e da saída UTF-8 do CLI.
- `test_editorial_qa.py` (13 testes) cobre a auditoria do acervo real (10 campanhas, 5 lentes, nenhum erro) e, em sandbox, linha de SRT longa, U+FFFD e mojibake, violação de guardrail, filtro por tenant, `--strict`, `--json`, divergência de duração, pacote social ausente, bloco vazio, saída humana e determinismo sem efeito colateral.
- `test_devlog_sync.py` (7 testes) cobre a consolidação da Etapa 3 (retrocompatibilidade byte a byte), a ordenação multi-etapa por `(etapa, agente)`, a atualização da linha `Fase atual`, a idempotência de execuções repetidas e o filtro `--pattern`.
- O CI também dispara com alterações em `05-review-portal/**`, `04-legendas/calendario-editorial.*`, `04-legendas/matriz-utm-consolidada.csv` e `docs/**`.
- **Gate `--strict`:** exige aprovação de todos os domínios. Com `04-legendas/matriz-utm-consolidada.csv` consolidada e nenhum bundle adulterado, `--json` e `--strict` retornam `ok: true` com todos os domínios ok e nenhum aviso. A auditoria editorial complementar (`editorial_qa.py`) é independente: no modo normal o acervo é aprovado com avisos de legibilidade, e `--strict` reprova enquanto houver linha de SRT acima de 48 caracteres.
- **Etapa 6:** as suítes dos módulos de operação do titular são acrescentadas na consolidação da etapa; a contagem de 21 módulos acima refere-se ao estado integrado até a Etapa 5B.
- **Etapa 13 — partição da suíte:** `tools/run_tests.py` classifica explicitamente os módulos de `tools/tests/` em `fast` (unitários e de contrato, sem render) e `render` (FFmpeg/FFprobe reais). A partição é fechada: um módulo novo não classificado reprova o runner com erro de uso, em vez de cair num grupo padrão. `--fast` é o padrão quando nenhuma flag de grupo é passada e é o gate 8 de `release_check.py`. A saída `--json` traz `ok`, `mode` (`smoke` / `fast` / `render` / `all`), `total`, `passed`, `failed`, `errors`, `skipped`, `durationSeconds`, `modules[]`, `results[]` e `archivesGuard`.

#### 5.1 Matriz de execução da suíte (Etapa 13.1)

As quatro faixas são **mutuamente exclusivas** na CLI; combinar duas retorna exit 2.

| Faixa | Composição | Módulos | Uso recomendado |
| --- | --- | --- | --- |
| `--smoke` | `fast` menos `HEAVY_CONTRACT_MODULES` | 24 | loop de desenvolvimento iterativo e pré-commit local |
| `--fast` | unitários e de contrato, sem render — **gate oficial** | 28 | gate 8 de `release_check.py`; CI sem FFmpeg |
| `--render` | módulos que renderizam via FFmpeg/FFprobe | 22 | validar o pipeline de mídia com as ferramentas portáteis instaladas |
| `--all` | `fast` + `render` | 50 | bateria integral antes de release |

`HEAVY_CONTRACT_MODULES` são os 4 módulos que **não renderizam mídia** mas dominam o tempo do gate completo, por criarem sandboxes Git completos, inicializarem ponte Node/MCP ou subirem servidores HTTP locais: `test_release_audit`, `test_studio_mcp`, `test_studio_connections`, `test_editorial_qa`. Eles permanecem em `fast` (o gate oficial continua cobrindo esses contratos) e ficam fora de `smoke`.

`smoke` é **derivado** de `FAST_MODULES` (`SMOKE_MODULES = tuple(m for m in FAST_MODULES if m not in HEAVY_CONTRACT_MODULES)`), portanto nunca diverge quando a classificação muda. Invariantes verificadas por `test_run_tests.py`: `smoke ⊂ fast` estritamente, `fast − smoke == HEAVY_CONTRACT_MODULES`, `smoke ∩ render == ∅` e nenhum `test_*.py` órfão fora de `fast ∪ render`.

**Custo medido nesta estação (Windows, FFmpeg 9.1 portátil):** `--smoke` 24 módulos / 354 testes / **53,4 s**; `--fast` 28 módulos / 422 testes / **375,4 s**. A meta de 15–20 s para `smoke` **não foi atingida** com a partição especificada: mesmo sem os 4 pesados, restam `test_executive_summary` (~10 s, geração real de relatórios e portais), `test_static_cards` (~10 s, desenho real de PNG em stdlib), `test_run_tests` (~5 s, subprocessos) e `test_review_dashboard` (~5 s). Atingir 15–20 s exigiria esvaziar testes legítimos ou redefinir a faixa, o que quebraria o contrato de composição. O ganho real de `smoke` sobre `fast` é de ~7×.

- **Etapa 13 — blindagem de masters:** toda execução do runner, em qualquer faixa, roda dentro de `archives_guard.ArchivesGuard`, que fotografa os SHA-256 de `.workspace/archives/` e restaura qualquer arquivo alterado ou removido, descartando mídia nova criada pelo teste. Os dois testes que historicamente sobrescreviam os masters (`test_audio_tts.py` e `test_factory_cli.py`) passaram a usar `archives_dir` isolado e instalam o guard em `setUpModule`, valendo também para `unittest` direto. `test_run_tests.py` cobre a partição, a saída `--json`, o restauro automático e a regressão do vazamento.
- **Etapa 13 — reparo e relatório executivo:** `test_workspace_doctor_repair.py` cobre dry-run sem mutação, detecção de mídia corrompida/ausente, restauração de conformidade SHA-256 com `--apply`, fail-closed por insumo ausente e por hash não reprodutível, regeneração apenas do derivado afetado, filtros por tenant/slug e recusa de path traversal. `test_executive_summary.py` cobre geração de JSON/Markdown, isolamento estrito entre os 5 tenants reais, selo `autoPublish: false`, incorporação de `bundleAttribution` / `promotionHistory` / fadiga com `zScore` e `pValue`, contenção de saída e integração com o portal.
- **Custo medido do gate `fast`:** na estação Windows de referência, o grupo `fast` roda em ~6 min; quatro módulos de contrato concentram ~90% do tempo (`test_release_audit`, `test_studio_mcp`, `test_studio_connections`, `test_editorial_qa`), por sandboxes Git, ponte Node e servidores HTTP — não por render. `test_studio_media` foi classificado em `render` porque renderiza de fato e sonda com ffprobe. O grupo `render` é adicional e exige as ferramentas portáteis instaladas.

## 6. Referências

- [docs/guia-operacional-titular.md](guia-operacional-titular.md) — rotina diária e semanal do titular: revisão, handoff, publicação manual e analytics.
- [docs/analytics-utm-playbook.md](analytics-utm-playbook.md) — eventos por nicho, configuração em GA4/Plausible/Umami e rotina semanal de UTM.
- [docs/guia-novo-nicho.md](guia-novo-nicho.md) — cadastrar um novo projeto/nicho em menos de 10 minutos.
- [docs/contexto/README.md](contexto/README.md) — estado atual, próximos passos e handoff.
- [WORKFLOW.md](../WORKFLOW.md) — fluxo editorial completo e regra de vídeo sem áudio.
- [AGENTS.md](../AGENTS.md) — regras do projeto, portabilidade entre estações e uso de `.workspace/`.
- [platform/README.md](../platform/README.md) — núcleo reutilizável (Studio, perfis de saída, provas HTTP).

