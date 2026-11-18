# NS-002 Piloto 01 — Agendamento online no Marca Salão

Entrega piloto ponta a ponta da campanha **NS-002** (`Agendamento online no Marca Salão`), parametrizada em `ns002-piloto.config.json` sobre a fixture editorial dedicada [`docs/fixtures/fixture-editorial-marca-salao.json`](../../docs/fixtures/fixture-editorial-marca-salao.json).

> **Estado editorial:** piloto técnico local em branch `codex/etapa1-piloto-ns002`. Aprovação para gravação e publicação continua dependente da revisão do titular.

---

## Política de produto e guardrails atendidos

- **Marca explícita:** todas as cenas exibem **Marca Salão** no cabeçalho superior (`headerOverlay`), substituindo qualquer referência legada a "Meu Salão".
- **Veracidade:** sem promessas de mensagens automáticas, lembretes 24h, confirmações via WhatsApp/SMS/e-mail, redução de faltas ou aumento de faturamento.
- **Sem pagamento simulado:** nenhuma tela ou botão de pagamento aparece no fluxo NS-002.
- **Separação de superfícies:** `/booking/marca-salao-modelo` mostra escolha de serviço/profissional, cálculo público de horários livres e confirmação; `/gestor/agenda` mostra apenas visualização e alteração manual de status.
- **Vídeo sem áudio (`-an`):** exportado em `1080×1920`, `30 fps`, H.264 (`yuv420p`), `30.0 s`, **0 streams de áudio**. Narração entregue exclusivamente em `.txt` separado para locução externa.

---

## Artefatos do pacote

| Artefato | Caminho | Versionado |
| --- | --- | --- |
| Configuração parametrizada (base para `brand-kit.json`) | `02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json` | sim |
| Vídeo MP4 vertical sem áudio | `02-reels-shorts/ns002-piloto-01/ns002-piloto-01.mp4` (cópia em `.workspace/archives/ns002-piloto-01/`) | não (`.gitignore` ignora `*.mp4`) |
| Storyboard 2×2 (segundos 2, 8, 16, 24) | `02-reels-shorts/ns002-piloto-01/preview-storyboard-ns002.png` | sim |
| Legendas sincronizadas (cópia no pacote) | `02-reels-shorts/ns002-piloto-01/ns002_roteiro_001.srt` | sim |
| Texto de narração externa (cópia no pacote) | `02-reels-shorts/ns002-piloto-01/ns002_roteiro_001_narracao.txt` | sim |
| Manifesto SHA-256 + medição FFprobe | `02-reels-shorts/ns002-piloto-01/manifest.json` | sim |

Fontes editoriais originais em [`04-legendas/`](../../04-legendas/):
- `04-legendas/ns002_roteiro_001.srt`
- `04-legendas/ns002_roteiro_001_narracao.txt`

---

## Cenas (30,0 s)

| # | ID | Intervalo | Superfície / Rota | Conteúdo visível |
| --- | --- | --- | --- | --- |
| 1 | `cena-01-hook` | 0–4 s | Marca Salão | Pergunta de abertura (`NS-002-H01`) |
| 2 | `cena-02-escolha` | 4–10 s | `/booking/marca-salao-modelo` | Escolha de serviço e profissional (`fixture-editorial`) |
| 3 | `cena-03-confirma` | 10–17 s | `/booking/marca-salao-modelo` | Seleção de horário livre (`09:00`) e resumo sem pagamento |
| 4 | `cena-04-ponte` | 17–20 s | `/booking/marca-salao-modelo` | Confirmação `"Agendamento realizado"` |
| 5 | `cena-05-salao-ve` | 20–26 s | `/gestor/agenda` | Agenda do gestor com `Ana Beatriz Souza` em `Confirmado` |
| 6 | `cena-06-cta` | 26–30 s | Marca Salão | CTA `"Conheça o agendamento online no Marca Salão"` + `marcasalao.com.br` |

---

## Reprodução local

```bash
python tools/ns002_pilot.py \
  --config 02-reels-shorts/ns002-piloto-01/ns002-piloto.config.json \
  --staging .workspace/tmp/ns002-piloto-01 \
  --archive .workspace/archives/ns002-piloto-01 \
  --json
```
