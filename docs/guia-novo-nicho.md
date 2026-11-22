# Guia Prático: Cadastrar um Novo Projeto ou Nicho Multi-Tenant (< 10 min)

Este guia mostra como adicionar um **4º, 5º ou N-ésimo projeto/nicho** na fábrica de vídeo programático em `tenants/<novo-nicho>/`, mantendo validação automática por schema, proteção de guardrails e renderização em lote via `tools/factory_cli.py`.

> **Nota de 22/11/2026:** existe também o onboarding automatizado
> `tools/tenant_scaffolder.py` (Etapa 14), com `--dry-run`/`--apply`. Ele **ainda não é
> fail-closed**: grava antes de validar, retorna `ok: true` mesmo com validação falha e não
> roda `editorial_qa`; o timing das cenas geradas também diverge do `format.duration`.
> Prefira este guia manual até as correções do backlog
> ([docs/contexto/PROXIMOS-PASSOS.md](contexto/PROXIMOS-PASSOS.md)) serem implementadas.
> Lembrete: adicionar tenant/campanha muda o mínimo estrutural de semanas do calendário
> (`ceil(n/4) + ceil(n/6)`); use `--weeks` adequado ou `--simulate-capacity` para planejar.

---

## Pré-requisitos locais

- Python 3.12+ (ou o ambiente em `.workspace/tools/venv/Scripts/python.exe`)
- `ffmpeg` e `ffprobe` no `PATH` (ou em `.workspace/tools/ffmpeg/`)
- Todos os arquivos criados estritamente dentro da raiz do checkout (`<RAIZ>`).

---

## Passo 1 — Criar a estrutura de pastas (`1 min`)

Escolha um identificador em `kebab-case` (apenas `a-z`, `0-9` e `-`), por exemplo `estudio-fitness`:

```text
tenants/estudio-fitness/
├── brand-kit.json
├── guardrails.json
├── fixtures/
│   └── fixture-editorial-estudio-fitness.json
└── campaigns/
    ├── README.md
    └── camp-shorts-estudio-fitness-001.json
```

---

## Passo 2 — Definir `brand-kit.json` (`2 min`)

Contrato validado por [`schemas/brand-kit.schema.json`](../schemas/brand-kit.schema.json).  
Você pode copiar `tenants/marca-salao/brand-kit.json` (preset `saas-demo`) ou `tenants/multitrack-hub/brand-kit.json` (preset `shorts-completo`) e ajustar:

```json
{
  "schemaVersion": 1,
  "tenantId": "estudio-fitness",
  "brandName": "Estúdio Fitness",
  "displayTitle": "ESTUDIO FITNESS",
  "monogram": "EF",
  "domain": "estudiofitness.com.br",
  "url": "https://estudiofitness.com.br",
  "tagline": "TREINOS E HORARIOS ORGANIZADOS",
  "palette": {
    "primary": "#22C55E",
    "secondary": "#38BDF8",
    "accent": "#FACC15",
    "background": "#0B1120",
    "surface": "#162033",
    "textPrimary": "#F8FAFC",
    "textMuted": "#94A3B8",
    "rgb": {
      "backgroundTop": [11, 17, 32],
      "backgroundBottom": [19, 28, 48],
      "headerBg": [8, 12, 24],
      "cardBg": [22, 32, 51],
      "cardHighlight": [32, 46, 74],
      "primaryAccent": [34, 197, 94],
      "secondaryAccent": [56, 189, 248],
      "statusConfirmed": [34, 197, 94],
      "statusWaiting": [250, 204, 21],
      "statusDone": [148, 163, 184],
      "textPrimary": [248, 250, 252],
      "textMuted": [148, 163, 184]
    }
  },
  "typography": { "fontFamily": "Arial", "titleWeight": "bold", "bodyWeight": "regular" },
  "headerOverlay": {
    "enabled": true,
    "label": "ESTUDIO FITNESS",
    "badgeText": "PROGRAMACAO & AULAS",
    "bgColor": "#080C18",
    "textColor": "#F8FAFC",
    "height": 170
  },
  "subtitleStyle": "Fontname=Arial,Fontsize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=0,Alignment=2,MarginV=34",
  "defaultPreset": "shorts-completo",
  "utmDefaults": { "utm_source": "youtube", "utm_medium": "shorts", "utm_campaign_prefix": "ef" }
}
```

> **Presets suportados:** `"saas-demo"` (cenas de app B2B/agenda/booking) ou `"shorts-completo"` (hook, catálogo/projetos, métricas, cards e CTA).

---

## Passo 3 — Definir `guardrails.json` (`2 min`)

Contrato validado por [`schemas/guardrails.schema.json`](../schemas/guardrails.schema.json):

```json
{
  "schemaVersion": 1,
  "tenantId": "estudio-fitness",
  "forbiddenClaims": ["emagrecimento garantido", "resultado 100% garantido", "sem esforço"],
  "forbiddenUiElements": ["checkout simulado"],
  "audioPolicy": {
    "allowAudioTrack": true,
    "requireExternalNarration": false,
    "requireSrt": true
  }
}
```

- Se o projeto proibir faixa sonora (como `marca-salao` e `meu-salao`), defina `"allowAudioTrack": false`, `"requireExternalNarration": true` e `"ffmpegFlag": "-an"`. O motor forçará `-an` (**0 streams de áudio**) e recusará `--audio`.

---

## Passo 4 — Criar a Fixture Editorial e a Campanha (`3 min`)

1. **Fixture** (`tenants/estudio-fitness/fixtures/fixture-editorial-estudio-fitness.json`):
   - Deve declarar `"tenantId": "estudio-fitness"` e dados fictícios plausíveis.
   - **Proibido conter placeholders de teste técnico** (`lorem ipsum`, `user1`, `test_user`, `e2e-...`, `12.000,00`).
   - **Compatibilidade com o preset `saas-demo`:** mesmo que seu nicho adote nomes próprios no JSON (por exemplo `instrutores`, `modalidades`, `gradeHorarios` em estúdios de Pilates como `tenants/estudio-flow/`), mantenha também as chaves estruturais lidas pelo motor bitmap (`profissionais`, `servicos`, `agenda.atendimentos` e `booking.rota`).
2. **Campanha** (`tenants/estudio-fitness/campaigns/camp-shorts-estudio-fitness-001.json`):
   - Copie o template mais próximo (`tenants/multitrack-hub/campaigns/camp-shorts-completo-multitrack-001.json` para `shorts-completo`, ou `tenants/marca-salao/campaigns/camp-saas-demo-marca-salao-001.json` / `tenants/estudio-flow/campaigns/camp-saas-demo-estudio-flow-001.json` para `saas-demo`).
   - Ajuste `"id"`, `"campaignId"`, `"tenantId"`, os tempos (`scenes[].duration` somando `format.duration`) e os textos de `"caption"` / `"narrationText"`.

---

## Passo 5 — Validar Contratos, Listar e Renderizar (`2 min`)

```bash
# 1. Validar schema, fixture e guardrails do novo tenant
python tools/tenant_validator.py --tenant estudio-fitness --json

# 2. Conferir descoberta na fábrica
python tools/factory_cli.py list --tenant estudio-fitness

# 3. Renderizar apenas o novo tenant (gera MP4, SRT, TXT, storyboard 2x2 e manifest.json)
python tools/factory_cli.py render --tenant estudio-fitness --json

# Em worktrees/branches paralelas, evite sobrescrever o factory-report.json compartilhado:
python tools/factory_cli.py render --tenant estudio-fitness --report .workspace/tmp/estudio-fitness-report.json --json

# 4. (Opcional) Validar todos os contratos e rodar os testes automatizados
python tools/tenant_validator.py --all --json
python -m unittest tools/tests/test_tenant_contracts.py tools/tests/test_factory_cli.py -v
```

Os artefatos são gravados transacionalmente em `02-reels-shorts/deliveries/estudio-fitness/<slug>/`, a cópia de vídeo fica arquivada em `.workspace/archives/<slug>/` (ignorada no Git por `*.mp4` em `.gitignore`) e o índice consolidado é atualizado em `02-reels-shorts/deliveries/factory-report.json` (ou no caminho passado em `--report`).

> **Nota sobre testes globais com novo tenant:** `tools/tests/test_tenant_contracts.py` (`test_07_cli_exit_codes`) e `tools/tests/test_factory_cli.py` (`test_01`/`test_03`) originalmente fixavam a contagem `3` para os tenants iniciais. Ao integrar o 4º+ nicho na `main`, atualize essas asserções ou torne-as dinâmicas (`>= 3`) e re-execute `python tools/factory_cli.py render --all --json`.

> **Nota sobre `.gitattributes` no Windows:** `.gitattributes` garante `eol=lf` para `tenants/**/*.json` e `02-reels-shorts/**` (`.srt`, `*_narracao.txt`, `*.json`), preservando os hashes SHA-256 idênticos entre worktrees e CI Linux.

---

## Passo 6 — Fluxo completo pós-criação (`2 min`)

Depois de validar e renderizar o vídeo (Passo 5), complete o ciclo de entrega com as ferramentas já existentes. Em worktrees/branches paralelas, direcione relatórios e saídas intermediárias para `.workspace/tmp/<tarefa>/` para não sobrescrever artefatos compartilhados.

```bash
# 1. Vídeo — MP4 1080x1920@30 sem faixa de áudio, SRT e narração TXT
python tools/factory_cli.py render --tenant estudio-fitness --report .workspace/tmp/estudio-fitness-report.json --json

# 2. Stories e Carrossel estáticos (kits 1080x1920 e 1080x1080 derivados das campanhas)
python tools/static_cards.py --tenant estudio-fitness --types stories,carousel --json

# 3. Derivados multiformato (cover, 1:1, 16:9) e derivatives.json por campanha
python tools/derivative_formats.py --tenant estudio-fitness --json

# 4. Pacotes sociais por entrega (uma entrega: --tenant <slug> --slug <id-da-entrega>)
python tools/publish_pack.py --all --json

# 5. Calendário editorial de 4 semanas e matriz UTM
python tools/campaign_calendar.py --start-date 2026-11-23 --weeks 7 --json

# 6. Portal de revisão humana (somente leitura) e auditoria de release
python tools/review_dashboard.py --build --json
python tools/review_dashboard.py --serve --port 8765        # abra http://127.0.0.1:8765
python tools/release_audit.py --strict --json               # gate: avisos também reprovam
python tools/devlog_sync.py --json                          # consolida devlogs no contexto_projeto.md
```

> **Publicação é manual:** `publish_pack.py` grava pacotes com `autoPublish: false` e `campaign_calendar.py` nasce com `statusEditorial: "aguardando_aprovacao_titular"`. Nenhuma ferramenta deste repositório publica, agenda ou cria rascunho nas redes. O portal `05-review-portal/` é instrumento de revisão: o titular aprova e publica fora daqui.

---

## Nicho regulado (saúde/estética) — referência oficial `clinica-vital`

O tenant `tenants/clinica-vital/` é a **referência oficial** do projeto para nichos regulados (saúde, clínicas, consultórios e estúdios de estética). Nele, a peça pública não pode prometer resultado clínico ou estético, diagnosticar à distância, expor dados sensíveis ou sugerir automação de contato. Use este tenant como base — e não os tenants de salão — ao cadastrar um novo nicho regulado.

### Estrutura

```text
tenants/clinica-vital/
├── brand-kit.json
├── guardrails.json
├── fixtures/
│   └── fixture-editorial-clinica-vital.json
└── campaigns/
    ├── README.md
    ├── camp-saas-demo-clinica-vital-001.json
    └── camp-saas-demo-clinica-vital-002.json
```

### Identidade e preset

- Paleta clínico-moderna: Azul Petróleo `#0EA5E9` (primary), Verde Menta `#14B8A6` (secondary), Âmbar Suave `#F59E0B` (accent) e Azul Profundo `#0B1324` (background).
- `defaultPreset: "saas-demo"`, `utmDefaults` (`instagram` / `reels` / `cv`), `audioPolicy` com `allowAudioTrack: false`, `requireSrt: true`, `requireExternalNarration: true` e `ffmpegFlag: "-an"`.

### Superfícies separadas por contrato

| Rota | `surface` | Responsabilidades permitidas |
| --- | --- | --- |
| `/avaliacao/[clinicId]` | `public-booking` | escolha de procedimento e especialista, seleção de horário livre e confirmação da avaliação, com paciente fictícia |
| `/gestor/consultas` | `manager-agenda` | grade de consultas, filtro por especialista e status, busca por paciente e alteração **manual** de status |

`routeRules` em `guardrails.json` torna essa separação auditável: a rota pública não pode exibir pagamento, diagnóstico online, prontuário ou promessa de cura; a rota da recepção não pode calcular horários livres nem exibir slots de marcação.

### Guardrails obrigatórios do nicho

- `forbiddenClaims`: cura/promessa de cura, resultado estético garantido, tratamento sem dor garantido, diagnóstico médico ou odontológico online, antes e depois, mensagens automáticas por WhatsApp/SMS/e-mail, lembretes automáticos de 24h, redução de faltas/zero absenteísmo e aumento de faturamento.
- `forbiddenUiElements`: checkout/pagamento/cobrança, prontuário médico sensível, receita digital, fotos antes/depois, `Meu Salão`, `E2E` e `Lorem ipsum`.

### Compatibilidade com o motor `saas-demo`

A fixture usa nomes próprios do nicho (`especialistas`, `procedimentos`, `gradeDiaria.consultas`) e replica as chaves estruturais lidas pelo motor bitmap: `profissionais`, `servicos`, `agenda.atendimentos` e `booking.rota`.

### Campanhas de referência

- `camp-saas-demo-clinica-vital-001.json`: jornada pública em `/avaliacao/clinica-vital-centro` → recepção em `/gestor/consultas` (paciente fictícia Patricia Monteiro), 6 cenas, `30.0s`.
- `camp-saas-demo-clinica-vital-002.json`: rotina exclusiva da recepção em `/gestor/consultas` (filtro por especialista, status manual e busca por paciente), sem cenas de `/avaliacao`, 6 cenas, `30.0s`.

### Validação, render e fluxo completo

```bash
# Contratos e descoberta
python tools/tenant_validator.py --tenant clinica-vital --json
python tools/tenant_validator.py --all --json
python tools/factory_cli.py list --tenant clinica-vital
python -m unittest tools/tests/test_tenant_contracts.py -v

# Render e pós-criação (o mesmo fluxo do Passo 6, com --tenant clinica-vital)
python tools/factory_cli.py render --tenant clinica-vital --report .workspace/tmp/clinica-vital/report.json --json
python tools/static_cards.py --tenant clinica-vital --types stories,carousel --json
python tools/derivative_formats.py --tenant clinica-vital --json
python tools/publish_pack.py --all --json
python tools/campaign_calendar.py --start-date 2026-11-23 --weeks 7 --json
python tools/review_dashboard.py --build --json
python tools/release_audit.py --strict --json
```

> **Consolidação pós-bootstrap:** ao integrar o 5º tenant, ajuste as contagens fixas em `tools/tests/test_factory_cli.py` (`totalTenants`, `totalCampaigns` e o número de entregas) para o novo total e re-execute `python tools/factory_cli.py render --all --json` com `ffmpeg`/`ffprobe` disponíveis. Em `tools/tests/test_tenant_contracts.py`, as contagens globais usam `>= 4` para valer antes e depois do merge; a validação dos contratos clínicos é feita em memória e a checagem do tenant e das 2 campanhas no disco é condicional à existência de `tenants/clinica-vital/`.

---

## Apêndice (proposta documentada em 22/11/2026, não aplicada): exclude portável por estação

A higiene de `.workspace/` vive em `<RAIZ>/.git/info/exclude`, **local por estação**. Nesta
estação o bloco cobre `worktrees/`, `tools/`, `tmp/`, `archives/`, `logs/`, `studio/`,
`reports/`, `__pycache__/` e `*.pyc`, mas **não** cobre `bundles/` nem `snapshots/`; noutra
máquina esses diretórios apareceriam em `git status`. Proposta para decisão do titular:
adotar em toda estação nova o bloco completo abaixo (sem alterar o `.gitignore` versionado):

```gitignore
# Marca Salao: artefatos locais por estacao (nao versionar)
# Devlogs permanecem rastreaveis (usados em consolidacao via devlog_sync).
.workspace/worktrees/
.workspace/tools/
.workspace/tmp/
.workspace/archives/
.workspace/logs/
.workspace/studio/
.workspace/reports/
.workspace/bundles/
.workspace/snapshots/
__pycache__/
*.pyc
```

Aplicação por estação é operação local de configuração, fora do escopo desta consolidação
documental; registrar a decisão em `docs/contexto/ESTADO-ATUAL.md` quando tomada.
