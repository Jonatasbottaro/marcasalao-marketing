# Índice de entrega — NS-001-P001 editorial v1 (peça de revisão)

Data: 24/11/2026 · Operação Resultado 02 · branch `feat/ns-001-resultado02-producao`
(base `103b67e`, PR #32 não mesclado) · worktree `.workspace/worktrees/ns001-resultado02`.

**Natureza: material de revisão humana.** Aprovação editorial de produção registrada em
[REGISTRO-APROVACAO-2026-11-24.md](../../../00-briefings/campanhas/NS-001/REGISTRO-APROVACAO-2026-11-24.md).
**Publicação/agendamento: não autorizados.** CTA/destino/bio/UTM por canal: pendentes (decisão 7).

## Como assistir

- Abra `<RAIZ>/.workspace/worktrees/ns001-resultado02/.workspace/tmp/ns001-resultado02/entrega-v1/review.html`
  no navegador (players por perfil, links para MP4/SRT/TXT).
- Ou abra diretamente os MP4 listados abaixo (caminhos locais desta estação; mídias não versionadas).

## Vídeos (master 9:16 compartilhado pelos três destinos)

| Perfil | Caminho local (relativo à worktree) | FFprobe | SHA-256 |
| --- | --- | --- | --- |
| facebook-reels-video | `.workspace/tmp/ns001-resultado02/entrega-v1/facebook-reels-video/execution-v1-148faea912a5aa06a690aa2b10d4671e717bf7a3be68f4fd32d8f3e1d5c7d591-primary-output.mp4` | 1080x1920 30/1 fps h264/yuv420p, 47.0s, 0 faixas de áudio | `78017b98a6f3268b0b25dec7c64106b809a5192360e3acd3a4457b35f2e7816d` |
| instagram-reels-video | `.workspace/tmp/ns001-resultado02/entrega-v1/instagram-reels-video/execution-v1-feab3b6ebb47462af3b69456877b9ccbb3787a246a71312c64169bf5088ac7d7-primary-output.mp4` | 1080x1920 30/1 fps h264/yuv420p, 47.0s, 0 faixas de áudio | `78017b98a6f3268b0b25dec7c64106b809a5192360e3acd3a4457b35f2e7816d` |
| youtube-shorts | `.workspace/tmp/ns001-resultado02/entrega-v1/youtube-shorts/execution-v1-2fda4d1d7148f1ea907f740855e32c50d0b82501159408ceaa222a6842809cfc-primary-output.mp4` | 1080x1920 30/1 fps h264/yuv420p, 47.0s, 0 faixas de áudio | `78017b98a6f3268b0b25dec7c64106b809a5192360e3acd3a4457b35f2e7816d` |

Geometria idêntica nos três perfis (1080×1920@30): a mesma composição fonte é reutilizada,
com manifesto próprio por destino (exigência da Fase 8 do brief).

## Legendas e narração (versionados)

- SRT final sincronizado: [04-legendas/ns001_roteiro_001.srt](../../../04-legendas/ns001_roteiro_001.srt)
  (9 cues, 47,0 s, ≤ 2 linhas/cue, validado por `tools/srt_validate.py`).
- Narração PT-BR por cenas: [04-legendas/ns001_roteiro_001_narracao.txt](../../../04-legendas/ns001_roteiro_001_narracao.txt).
- Cópias por perfil nas entregas (`*-captions.srt`, `*-narration-script.txt`), idênticas ao SRT final.

## Capa

O fluxo VideoRequest v1 não possui campo de capa dedicada; foi extraída uma capa de
revisão do frame de abertura (0,5 s) na identidade opção A:
`entrega-v1/capa-revisao.png` (1080×1920, local). Capa publicitária por rede permanece
fora do escopo aprovado.

## Manifestos, hashes e validações

- `entrega-v1/index.json` + `entrega-v1/<perfil>/delivery-manifest.json` (SHA-256 recalculados na promoção).
- `entrega-v1/<perfil>/*-asset-manifest.json` (origem/licença por mídia).
- Pacote ZIP de revisão: `.workspace/tmp/ns001-resultado02/pacote-revisao-v1.zip`
  verificado por `tools/delivery_verify.py` (resultado em `.workspace/logs/ns001-resultado02/delivery-verify.json`).
- FFprobe: 1 stream de vídeo por arquivo, 0 streams de áudio (tabela acima).
- Pedido versionado: [pedido-editorial-v1.video-request.json](pedido-editorial-v1.video-request.json).
- Fixture: [fixture-summary.json](fixture-summary.json) (namespace `editorial-ns001-20261124`, Salão Harmonia).

## Pendências reais

1. Decisão 7 do pacote: CTA/destino/bio/UTM por canal (bloqueia publicação, não a revisão).
2. Nome público oficial do produto ("Marca Salão" × "Meu Salão") — recorte exclui a sidebar; decisão futura.
3. Correção localizada TC-01: estilo ASS de legendas tornado geométrico em `tools/render_local.py`
   (`build_subtitle_style`), para cumprir a faixa segura y≈1450–1650 e ≤2 linhas do storyboard aprovado;
   constantes legadas preservadas para consumidores antigos; testes de render reexecutados.
4. Mídias (MP4) não versionadas por política do repositório (`*.mp4` ignorado); existem apenas nesta estação.
5. Revisão humana do titular pendente — esta entrega não é campanha aprovada para publicação.

## Evidências locais (não versionadas)

- `.workspace/logs/ns001-resultado02/`: studio-check, plan, renders, testes, ffprobe, delivery-verify, produtividade.
- `.workspace/tmp/ns001-resultado02/qc/`: frames de inspeção visual (fontes e composição final).
- `.workspace/tmp/ns001-resultado02/videos/`: frames brutos das gravações e marcas de tempo.
