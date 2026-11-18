# Campanhas — Tenant Multitrack Hub

Configurações de campanhas do nicho **Multitrack Hub** (`multitrack-hub`), no preset `shorts-completo` (1080×1920 @ 30 fps, com faixa de áudio AAC quando `allowAudioTrack: true`).

- Brand kit: [`../brand-kit.json`](../brand-kit.json)
- Guardrails: [`../guardrails.json`](../guardrails.json)
- Fixture editorial: [`../fixtures/fixture-editorial-multitrack-hub.json`](../fixtures/fixture-editorial-multitrack-hub.json)
- Destino oficial: `https://multitrackhub.com.br` (rateios: `https://multitrackhub.com.br/rateios`)

## Campanhas

| Slug | Foco | Cenas | Duração |
| --- | --- | --- | --- |
| `camp-shorts-completo-multitrack-001` | Visão geral: catálogo, métricas, stems e rateios | 5 | 30,0 s |
| `camp-shorts-rateios-002` | Organização de **rateios** de multitracks (cotas, faixas, vagas) | 5 | 30,0 s |
| `camp-shorts-stems-workflow-003` | Organização de **stems** Click/Guide/Banda e ordem de trabalho | 5 | 30,0 s |

## Renderização com áudio

As campanhas `multitrack-hub` permitem faixa de áudio (`allowAudioTrack: true`). A trilha `.wav` é gerada por `tools/audio_tts.py` e injetada via `--audio` do `tools/preset_runner.py`:

```text
python tools/audio_tts.py --tenant multitrack-hub \
  --output .workspace/tmp/audio-mth/bed-30s.wav --duration 30 --mode ambient-bed

python tools/preset_runner.py --tenant multitrack-hub \
  --config tenants/multitrack-hub/campaigns/camp-shorts-rateios-002.json \
  --output-dir 02-reels-shorts/deliveries/multitrack-hub/camp-shorts-rateios-002 \
  --audio .workspace/tmp/audio-mth/bed-30s.wav
```