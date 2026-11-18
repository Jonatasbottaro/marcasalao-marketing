# Prova local — NS-001 Reels (Video Studio)

## Resumo

A peça piloto da NS-001 (NS-001-P001, "Organização e visibilidade da agenda — Reels") foi montada como `VideoRequest v1` com **7 cenas somando 30 segundos** e submetida ao **pré-voo real** (`--plan-only --json`) do Video Studio, que foi aprovado com sucesso.

O **render real** ficou **bloqueado por causa externa**: `ffmpeg` e `ffprobe` não estão instalados nesta estação e não há conexão com internet para obtê-los (a instalação temporária está autorizada apenas dentro de `<RAIZ>/.workspace/`). Nenhuma mídia final (MP4/SRT/TXT) foi produzida; trata-se de uma **prova técnica**, não de mídia final.

## Pedido montado (versionado)

- Arquivo: `tools/produce/examples/marca-salao-ns-001-p001.video-request.json`
- requestId: `marca-salao-ns-001-p001`
- Campanha: ns-001 | Peça: NS-001-P001 | Canal: instagram | Formato: reels
- Perfis: instagram-reels-video, facebook-reels-video, youtube-shorts
- Duração total: 30 000 ms (30 s), 7 cenas
- Geometria: 1080 × 1920, 9:16 | FPS: 30
- Áudio: nenhuma etapa (regra de vídeo sem áudio, exportação com `-an`)
- Mídia: 7 PNGs fictícios 1080×1920 em `.workspace/tmp/ns-001-p001/assets/` (`origin: synthetic-demo`), um por cena

## Sequência das 7 cenas (conforme PILOTO-NS-001-REELS.md)

| # | Cena | Duração | narrativeFunction | Texto de tela |
|---|------|---------|-------------------|---------------|
| 1 | Hook — pergunta de clareza | 4 000 ms | hook | "Você consegue visualizar os agendamentos do seu salão com clareza?" |
| 2 | Situação — informação espalhada | 6 000 ms | demonstration | "Quando as informações ficam espalhadas, cada lugar mostra um pedaço do dia." |
| 3 | Visões dia/semana/mês | 6 000 ms | demonstration | "O mesmo registro, visto por dia, semana ou mês." |
| 4 | Filtros e busca | 6 000 ms | demonstration | "Filtrar por profissional, por status, ou buscar pelo nome." |
| 5 | Detalhes do atendimento fictício | 4 000 ms | demonstration | "Abrir um atendimento e ver os dados dele." |
| 6 | Ação de status (Confirmar) | 2 000 ms | demonstration | "Atualizar o status do atendimento." |
| 7 | CTA | 2 000 ms | cta | "Conheça a agenda do Marca Salão." |

Total: 30 000 ms (30 s).

## Resultado do pré-voo real (aprovado)

Arquivo: `prova-local/pre-voo.json` (resumo em `prova-local/pre-voo-resumo.md`)

| Campo | Valor |
|-------|-------|
| status | preview |
| requestId | marca-salao-ns-001-p001 |
| Perfis compilados | 3 (instagram-reels-video, facebook-reels-video, youtube-shorts) |
| status por perfil | compiled (todos) |
| failureCode | null (nenhum) |
| errors | [] (nenhum) |
| Geometria | 1080 × 1920, 9:16 |
| FPS | 30 |
| Duração total | 30 000 ms (30 s) |
| supported | true (todos) |
| renderer.adapter | undecided (aviso não-bloqueante) |
| Regras de publicação | OUTPUT_PLAN_CONTEXT_NOT_DECLARED (avisos não-bloqueantes) |

Os três perfis estão estruturalmente válidos para render. O perfil principal (instagram-reels-video) tem 7 beats, duração 30s, sem erros.

## Resultado do render real (bloqueado)

Arquivo: `prova-local/render-instagram.json`

| Campo | Valor |
|-------|-------|
| status | partial |
| overallStatus | partial |
| completedCount | 0 |
| lastValidDelivery | null |
| Erro do perfil instagram-reels-video | `ffmpeg/ffprobe nao encontrados; exponha no PATH ou em .workspace/tools/ffmpeg` |

## Causa específica do bloqueio (render)

O Video Studio (`tools/produce_video.py`) exige `ffmpeg` e `ffprobe` para a etapa de render (staging → render FFmpeg `-an` → inspeção FFprobe → validação SRT/narração → promoção transacional). Nenhuma das duas ferramentas está disponível:
- Não estão no PATH do sistema.
- Não existem em `.workspace/tools/ffmpeg/`.
- Não há conexão com internet nesta estação para baixar um ffmpeg portátil (fonte usada pelo projeto: BtbN ffmpeg-release-builds).

## O que é necessário para concluir o render (pendente — depende do ambiente)

1. Expor `ffmpeg` e `ffprobe` no PATH do processo, ou colocá-los em `.workspace/tools/ffmpeg/` (conforme `tools/render/README.md`, seção "Requisitos").
2. Reexecutar: `python tools/produce_video.py --input tools/produce/examples/marca-salao-ns-001-p001.video-request.json --profile instagram-reels-video --output-dir <entrega> --json`
3. Após o render, inspecionar com `ffprobe`: dimensões 1080×1920, 0 faixas de áudio, codec H.264, yuv420p, duração ~30s.
4. Verificar as 7 cenas, o SRT e a legibilidade dos textos em enquadramento de celular (390 × 844).

## Mídia usada no teste (fictícios — precisam de substituição)

Todos os 7 PNGs são **substitutos claramente marcados como fictícios** (`origin: synthetic-demo`). Para a peça final, devem ser substituídos por capturas reais com fixture editorial, revisão de marca e aprovação do titular (ver PILOTO-NS-001-REELS.md, seção 4). As capturas que ainda faltam:
- Cena 3: visões dia/semana/mês da agenda (captura nova com fixture editorial)
- Cena 4: filtros por profissional/status + busca (captura nova com fixture editorial)
- Cena 5: modal de detalhes (horário, cliente, profissional, serviço, preço, status) — dados fictícios
- Cena 6: ação Confirmar (Pendente → Confirmado) — com persistência após recarga
- Cena 7: arte final com CTA — identidade da marca, sem botão clicável desenhado

## Onde ficam as evidências

- `prova-local/PROVA-LOCAL.md` — este resumo
- `prova-local/pre-voo.json` — resultado bruto do pré-voo
- `prova-local/pre-voo-resumo.md` — resumo legível do pré-voo
- `prova-local/render-instagram.json` — resultado do render parcial (bloqueado)
- `PILOTO-NS-001-REELS.md` — sequência por cena, inventário de mídias, rascunho de legenda/CTA, registro de publicação
- `legenda-rascunho.md` — rascunho da legenda e posicionamento do CTA
- `registro-publicacao.csv` — registro de publicação iniciado (campos de horário/link/métricas vazios)
- `APROVEITAMENTO-NS-002.md` — reaproveitamento para a NS-002

## Regra de vídeo sem áudio

Respeitada integralmente: nenhum áudio foi gerado ou preservado; o pipeline está configurado para exportar com `-an`; nenhum TTS, música ou efeito sonoro foi usado.

## Estado do MP4

**Não há MP4.** O render real está bloqueado pela ausência de `ffmpeg`/`ffprobe` (causa documentada acima). Este piloto entrega o pedido versionado, os assets fictícios, o pré-voo aprovado e a causa específica do bloqueio. A entrega concluída (MP4) fica para quando o ambiente tiver ffmpeg/ffprobe disponível.
