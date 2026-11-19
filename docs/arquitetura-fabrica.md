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

Pacote social correspondente em `04-legendas/pacotes-publicacao/<tenant>/<slug>/` (`instagram-reels.md`, `youtube-shorts.md`, `facebook-reels.md`, `checklist-publicacao.json` com `autoPublish: false`). **Nada publica sozinho**: publicação é sempre manual e exige autorização específica.

```
schemas/  ─┐
           ├─> tenant_validator ─> preset_runner ─(+ audio_tts*)─> deliveries/<tenant>/<slug>/
tenants/ ──┤                                                              │
           │                     factory_cli (lote: list/render)          v
           │                                                          publish_pack
           │                                                              │
           │                                                              v
           └──────────────────────────────────────────────> release_audit (gate de release)
                                           devlog_sync (registro de sessões no contexto_projeto.md)
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

### 2.8 `tools/release_audit.py` — gate de release (Agente 4, Etapa 4)

Auditor final de prontidão em uma passada (`python tools/release_audit.py [--strict] [--json] [--root <raiz>]`):

| Grupo | Checks | Falha |
| --- | --- | --- |
| Tenants | ≥ 4 válidos via `tenant_validator` (`strict=False`, agregando erros) | Inválido ou insuficiente |
| Entregas | Por campanha: diretório, `manifest.json`, `<slug>.srt`, `<slug>_narracao.txt`, `preview-storyboard.png` com SHA-256 e bytes conferidos; vídeo presente em disco tem hash conferido | Arquivo/manifesto ausente, hash ou tamanho divergente |
| Pacotes | `checklist-publicacao.json` presente com `autoPublish: false` | Pacote ausente, checklist inválido, auto-publicação ativa |
| Higiene Git | `git ls-files "*.mp4" "*.wav"` vazio; regras `eol=lf` no `.gitattributes`; worktrees históricas (`prova-campanha-conclusao`, `studio-package-verify2`) preservadas | Mídia rastreada, sem `eol=lf`, worktree registrada sem diretório |

Avisos (não reprovam no modo normal; **reprovam com `--strict`**): vídeo não versionado ausente no disco, worktree histórica ausente na estação e worktree órfã (diretório sem registro). O modo normal é executável em qualquer estação/CI; o `--strict` é o gate da estação de release, que possui os vídeos.

Exit codes: `0` aprovado; `1` reprovado; `2` erro de uso/execução.

### 2.9 `tools/devlog_sync.py` — registro de sessões (Agente 4, Etapa 4)

Consolida devlogs `.workspace/devlogs/etapa*-agente*.md` no `contexto_projeto.md` (Seção 1 "Estado atual" + Seção 7 "Histórico de sessões"), com ordenação numérica por `(etapa, agente)`, idempotência por marcador `<!-- devlog-sync:<arquivo> -->` e retrocompatibilidade total com os registros da Etapa 3. `--pattern` restringe a descoberta (padrão `etapa*-agente*.md`); o resultado JSON reporta `pattern` e a etapa/agente de cada entrada. A consolidação é idempotente: re-execuções não duplicam entradas já aplicadas. CLI: `python tools/devlog_sync.py [--pattern <glob>] [--json]`.

### 2.10 Módulos previstos da Etapa 4 (em desenvolvimento paralelo)

`derivative_formats` (formatos derivados), `review_dashboard` (painel de revisão) e `campaign_calendar` (calendário de campanhas) estão previstos no fluxo da Etapa 4 e **ainda não estão presentes nesta branch** — são desenvolvidos em paralelo pelos Agentes 1–3. Ao serem integrados na main, atualize o diagrama da Seção 1 e acrescente a seção correspondente aqui.

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

# 4. Pacotes sociais (autoPublish: false)
python tools/publish_pack.py --all

# 5. Auditoria de prontidão (qualquer estação/CI)
python tools/release_audit.py --json

# 6. Gate de release (na estação com os vídeos em disco)
python tools/release_audit.py --strict --json

# 7. Consolidar o registro de sessões no contexto do projeto (idempotente)
python tools/devlog_sync.py --json
```

Para cadastrar um 5º nicho/tenant, siga [docs/guia-novo-nicho.md](guia-novo-nicho.md) (estrutura, schemas, fixture, campanha, validação e render em menos de 10 minutos).

## 5. Testes e CI

Suíte da fábrica (CI: `.github/workflows/local-render-validation.yml`, etapa "Validar contratos multi-tenant e suites da fabrica"):

```bash
python -m unittest tools/tests/test_tenant_contracts.py tools/tests/test_preset_runner.py \
  tools/tests/test_factory_cli.py tools/tests/test_audio_tts.py tools/tests/test_publish_pack.py \
  tools/tests/test_devlog_sync.py tools/tests/test_release_audit.py -v
```

- `test_release_audit.py` (11 testes) cobre aprovação completa no repositório atual, baseline do sandbox (aprova no modo normal e reprova no `--strict`) e falhas simuladas: hash corrompido, arquivo ausente, diretório de entrega ausente, `autoPublish: true`, pacote ausente, mídia rastreada, `.gitattributes` sem `eol=lf`, worktree órfã e worktree registrada sem diretório.
- `test_devlog_sync.py` (7 testes) cobre a consolidação da Etapa 3 (retrocompatibilidade byte a byte), a ordenação multi-etapa por `(etapa, agente)`, a idempotência de execuções repetidas e o filtro `--pattern`.
- Registro local desta branch: **53 testes em 7 módulos, todos verdes** (incluindo renders reais do `preset_runner`).
- **Pendência de consolidação:** a linha do CI ainda não inclui `tools/tests/test_release_audit.py` (o workflow está fora do território deste agente). Ao consolidar a Etapa 4 na main, acrescente o módulo à etapa "Validar contratos multi-tenant e suites da fabrica".

## 6. Referências

- [docs/guia-novo-nicho.md](guia-novo-nicho.md) — cadastrar um novo projeto/nicho em menos de 10 minutos.
- [docs/contexto/README.md](contexto/README.md) — estado atual, próximos passos e handoff.
- [WORKFLOW.md](../WORKFLOW.md) — fluxo editorial completo e regra de vídeo sem áudio.
- [AGENTS.md](../AGENTS.md) — regras do projeto, portabilidade entre estações e uso de `.workspace/`.
- [platform/README.md](../platform/README.md) — núcleo reutilizável (Studio, perfis de saída, provas HTTP).

