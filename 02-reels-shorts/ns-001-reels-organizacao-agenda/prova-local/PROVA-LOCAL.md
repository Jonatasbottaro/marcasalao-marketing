# Prova local — NS-001 Reels (Video Studio)

## Resumo

A peça piloto da NS-001 (NS-001-P001, "Organização e visibilidade da agenda — Reels") foi montada como `VideoRequest v1` com **7 cenas somando 30 segundos** e submetida ao **pré-voo e render real** (`tools/campaign_proof.py run --all-profiles`) nos perfis `instagram-reels-video`, `facebook-reels-video` e `youtube-shorts`.

Todos os três perfis concluíram em **1080×1920 @ 30 fps (H.264/yuv420p), duração exata 30.0 s e 0 faixas de áudio (`-an`)**, com arquivos `.srt` e roteiro `.txt` de narração validados. Todos os ativos visuais usam substitutos sintéticos marcados como `PROVA FICTICIA` (`origin: synthetic-demo`); trata-se de uma **prova técnica**, com aprovação editorial pendente para gravação ou publicação.

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

Arquivo: `prova-local/pre-voo.json` (gerado por `python tools/produce_video.py --input tools/produce/examples/marca-salao-ns-001-p001.video-request.json --plan-only --json`).

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

Os três perfis estão estruturalmente válidos para render. O perfil principal (`instagram-reels-video`) tem 7 beats, duração 30s, sem erros.

## Resultado do render real (concluído — prova técnica)

Arquivo: `prova-local/index.json` (`overallStatus: completed`, `completedCount: 3`, gerando entregas em `<RAIZ>/.workspace/archives/prova-campanha-ns001-ns002/ns-001-p001/`).

| Perfil | Status | Geometria / FPS | Duração | Áudio |
|--------|--------|-----------------|---------|-------|
| instagram-reels-video | completed | 1080×1920 @ 30 fps (h264/yuv420p) | 30.0 s | 0 faixas (`-an`) |
| facebook-reels-video | completed | 1080×1920 @ 30 fps (h264/yuv420p) | 30.0 s | 0 faixas (`-an`) |
| youtube-shorts | completed | 1080×1920 @ 30 fps (h264/yuv420p) | 30.0 s | 0 faixas (`-an`) |

## Comando reproduzível da prova completa

```bash
python tools/campaign_proof.py run tools/produce/examples/marca-salao-ns-001-p001.video-request.json --all-profiles --output-dir .workspace/archives/prova-campanha-ns001-ns002/ns-001-p001 --json
```

Para inspeção humana final antes da publicação:
1. Substituir os 7 PNGs sintéticos em `.workspace/tmp/ns-001-p001/assets/` por capturas reais aprovadas (ou passar mídia do operador antes do `prepare`, que preserva arquivos sem marcador sintético).
2. Validar visualmente as 7 cenas, `.srt`, `.txt` de narração e o HTML portável de revisão no celular (`390×844`) e desktop.

## Mídia usada no teste (fictícios — precisam de substituição)

Todos os 7 PNGs são **substitutos claramente marcados como fictícios** (`origin: synthetic-demo`). Para a peça final, devem ser substituídos por capturas reais com fixture editorial, revisão de marca e aprovação do titular (ver PILOTO-NS-001-REELS.md, seção 4). As capturas que ainda faltam:
- Cena 3: visões dia/semana/mês da agenda (captura nova com fixture editorial)
- Cena 4: filtros por profissional/status + busca (captura nova com fixture editorial)
- Cena 5: modal de detalhes (horário, cliente, profissional, serviço, preço, status) — dados fictícios
- Cena 6: ação Confirmar (Pendente → Confirmado) — com persistência após recarga
- Cena 7: arte final com CTA — identidade da marca, sem botão clicável desenhado

## Onde ficam as evidências

- `prova-local/PROVA-LOCAL.md` — este resumo
- `prova-local/pre-voo.json` — resultado bruto do pré-voo (`marca-salao-ns-001-p001`)
- `prova-local/index.json` — índice da entrega concluída para os 3 perfis (`completedCount: 3`)
- `<RAIZ>/.workspace/archives/prova-campanha-ns001-ns002/ns-001-p001/` — pacote portável com MP4s, `.srt`, `.txt`, miniaturas em `assets/` e `revisao-marca-salao-ns-001-p001.html`
- `PILOTO-NS-001-REELS.md` — sequência por cena, inventário de mídias, rascunho de legenda/CTA, registro de publicação
- `legenda-rascunho.md` — rascunho da legenda e posicionamento do CTA
- `registro-publicacao.csv` — registro de publicação iniciado (campos de horário/link/métricas vazios)
- `APROVEITAMENTO-NS-002.md` — reaproveitamento para a NS-002

## Regra de vídeo sem áudio

Respeitada integralmente: nenhuma faixa de áudio foi gerada ou preservada (`audioStreams: 0`, `-an`); nenhum TTS, música ou efeito sonoro foi usado.

## Estado do MP4 (prova técnica)

Entregas MP4/SRT/TXT concluídas em `<RAIZ>/.workspace/archives/prova-campanha-ns001-ns002/ns-001-p001/` com substitutos sintéticos claramente identificados (`PROVA FICTICIA`). Permanecem em estado editorial de **rascunho/prova técnica** até substituição por capturas reais aprovadas pelo titular.
