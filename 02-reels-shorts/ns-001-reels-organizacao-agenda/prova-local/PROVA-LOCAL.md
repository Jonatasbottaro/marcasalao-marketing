# Prova local — NS-001 Reels (Video Studio)

## Resumo

A peça piloto da NS-001 foi aberta no Video Studio e submetida ao **pré-voo** (`--plan-only`) com sucesso. O **render real** ficou bloqueado por causa específica: `ffmpeg/ffprobe não encontrados` no PATH nem em `.workspace/tools/ffmpeg/`. Nenhuma mídia final (MP4/SRT/TXT) foi produzida; trata-se de uma **prova técnica**, não de mídia final.

## Resultado do pré-voo

Arquivo: `pre-voo.json` (cópia em `prova-local/`)

| Campo | Valor |
|-------|-------|
| status | preview |
| requestId | marca-salao-social-reel-demo |
| Perfis compilados | 3 (instagram-reels-video, facebook-reels-video, youtube-shorts) |
| status por perfil | compiled (todos) |
| failureCode | null (nenhum) |
| errors | [] (nenhum) |
| Geometria | 1080 × 1920, 9:16 |
| FPS | 30 |
| Duração total | 14 s (3 cenas: 4s + 6s + 4s) |
| supported | true (todos) |
| renderer.adapter | undecided (aviso não-bloqueante) |
| Regras de publicação | OUTPUT_PLAN_CONTEXT_NOT_DECLARED (avisos não-bloqueantes; contexto não declarado no documento) |

Os três perfis estão estruturalmente válidos para render. A duração de 14s está abaixo da duração alvo de 30s proposta no PILOTO-NS-001-REELS.md (a duração final é pendente de leitura cronometrada e confirmação editorial).

## Resultado do render real

Arquivo: `index.json` (cópia em `prova-local/`)

| Campo | Valor |
|-------|-------|
| overallStatus | partial |
| profileCount | 3 |
| completedCount | 0 |
| lastValidDelivery | null (todos) |
| Erro por perfil | `ffmpeg/ffprobe não encontrados; exponha no PATH ou em .workspace/tools/ffmpeg` |

## Causa específica do bloqueio

O Video Studio (`tools/produce_video.py`) exige `ffmpeg` e `ffprobe` para a etapa de render (staging → render FFmpeg `-an` → inspeção FFprobe → validação SRT/narração → promoção transacional). Nenhuma das duas ferramentas está disponível:
- Não estão no PATH do sistema.
- Não existem em `.workspace/tools/ffmpeg/`.

## O que é necessário para concluir o render

1. Expor `ffmpeg` e `ffprobe` no PATH do processo, ou colocá-los em `.workspace/tools/ffmpeg/` (conforme documentado em `tools/render/README.md`, seção "Requisitos").
2. Reexecutar: `python tools/produce_video.py --input tools/produce/examples/marca-salao-social-reel.video-request.json --output-dir <entrega> --json`
3. Após o render, inspecionar com `ffprobe`: dimensões 1080×1920, 0 faixas de áudio, codec H.264, yuv420p, duração ~14s.

## Mídia usada no teste

- `tela-abertura.png` — PNG fictício 1080×1920, gerado localmente (gradiente sintético), `origin: synthetic-demo`
- `tela-demo.png` — PNG fictício 1080×1920, gerado localmente (gradiente sintético), `origin: synthetic-demo`

Ambos são **substitutos claramente marcados como fictícios**. Para a peça final, devem ser substituídos por capturas reais com fixture editorial, revisão de marca e aprovação do titular (ver PILOTO-NS-001-REELS.md, seção 4).

## Onde ficam as evidências

- `prova-local/pre-voo.json` — resultado do pré-voo
- `prova-local/index.json` — resultado do render parcial (bloqueado)
- `PILOTO-NS-001-REELS.md` — sequência por cena, inventário de mídias, rascunho de legenda/CTA, registro de publicação
- `legenda-rascunho.md` — rascunho da legenda e posicionamento do CTA
- `registro-publicacao.csv` — registro de publicação iniciado (campos de horário/link/métricas vazios)

## Regra de vídeo sem áudio

Respeitada integralmente: nenhum áudio foi gerado ou preservado; o pipeline está configurado para exportar com `-an`; nenhum TTS, música ou efeito sonoro foi usado.
