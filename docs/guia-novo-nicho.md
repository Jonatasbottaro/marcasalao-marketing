# Guia Prático: Cadastrar um Novo Projeto ou Nicho Multi-Tenant (< 10 min)

Este guia mostra como adicionar um **4º, 5º ou N-ésimo projeto/nicho** na fábrica de vídeo programático em `tenants/<novo-nicho>/`, mantendo validação automática por schema, proteção de guardrails e renderização em lote via `tools/factory_cli.py`.

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
