# Índice de entrega — NS-001-P001 editorial v2 (peça de revisão, Studio Bella)

Data: 25/11/2026 · Operação Resultado 08 — Studio Bella · checkout principal em `main`
(base `7f1c7ff`), alterações ainda não commitadas (commit/push pendentes de autorização do titular).

**Natureza: material de revisão humana.** A aprovação editorial de produção vigente continua sendo a da v1
([REGISTRO-APROVACAO-2026-11-24.md](../../../00-briefings/campanhas/NS-001/REGISTRO-APROVACAO-2026-11-24.md));
esta v2 não a substitui nem a altera. **Publicação/agendamento: não autorizados.**
A v1 e seus registros foram preservados sem edição.

## Diferença em relação à v1

- Fontes: 10 capturas reais do ambiente demonstrativo Studio Bella (CAP-01 a CAP-10),
  em vez dos assets de vídeo da Resultado 02 (indisponíveis nesta estação).
- Roteiro: mesmas 7 cenas e mesmos 47,0 s do storyboard aprovado, com o texto aprovado
  redistribuído em 14 beats para acompanhar as capturas (nenhuma frase nova; a cena 6
  atravessa CAP-09 pendente → CAP-10 confirmado).
- Correção técnica no motor existente: conversão explícita de range após a legenda queimada
  em `tools/render_local.py` (`scale=out_range=limited,format=yuv420p`), porque o libass
  remarca o quadro como full-range e o FFmpeg 9 não converte o range só com `format`.

## Como assistir

- Abra `<RAIZ>/.workspace/tmp/ns001-studio-bella-v2/entrega-v2/review.html` no navegador
  (players por perfil, legendas sincronizadas, links para MP4/SRT/TXT).
- Ou abra diretamente os MP4 listados abaixo (caminhos locais desta estação; mídias não versionadas).
- Frames de inspeção por cena: `entrega-v2/qc/frame-cena-01..07-*.jpg` (locais).

## Vídeos (master 9:16 compartilhado pelos três destinos)

| Perfil | Caminho local (relativo a `<RAIZ>`) | FFprobe | SHA-256 |
| --- | --- | --- | --- |
| instagram-reels-video | `.workspace/tmp/ns001-studio-bella-v2/entrega-v2/instagram-reels-video/execution-v1-e36382aaa54e5fc12aefbc9d5c7a1ab87aca818acf6d876fca92e3b9ab661a30-primary-output.mp4` | 1080x1920 30/1 fps h264/yuv420p (tv), 47.0s, 0 faixas de áudio | `63bef7c1d8c5760949e52bfd25e2e9e7e20ba0dc4ef3a4796de54e32e360b11b` |
| facebook-reels-video | `.workspace/tmp/ns001-studio-bella-v2/entrega-v2/facebook-reels-video/execution-v1-11b5f2d9f4a519cf2e203fd11423fb2fa949a9b8462d6ddac6106e5af710f03a-primary-output.mp4` | idem | `63bef7c1d8c5760949e52bfd25e2e9e7e20ba0dc4ef3a4796de54e32e360b11b` |
| youtube-shorts | `.workspace/tmp/ns001-studio-bella-v2/entrega-v2/youtube-shorts/execution-v1-5dcb4df27e9defb7ce3af4731064e0a4911b9ea5a454b0a3306e2482aaf75090-primary-output.mp4` | idem | `63bef7c1d8c5760949e52bfd25e2e9e7e20ba0dc4ef3a4796de54e32e360b11b` |

Geometria idêntica nos três perfis (1080×1920@30): a mesma composição fonte é reutilizada,
com manifesto próprio por destino. Hashes idênticos nos três MP4 (mesma composição).

## Legendas e narração (versionados, arquivos novos — v1 intacta)

- SRT v2 sincronizado (14 cues, 47,0 s, ≤ 2 linhas/cue, validado por `tools/srt_validate.py`):
  [04-legendas/ns001_roteiro_001_v2_studio_bella.srt](../../../04-legendas/ns001_roteiro_001_v2_studio_bella.srt).
- Narração PT-BR por beats/cenas:
  [04-legendas/ns001_roteiro_001_v2_studio_bella_narracao.txt](../../../04-legendas/ns001_roteiro_001_v2_studio_bella_narracao.txt).
- Cópias por perfil nas entregas (`*-captions.srt`, `*-narration-script.txt`); SRT idêntico nos três perfis.
- Os arquivos finais da v1 (`ns001_roteiro_001.srt` / `..._narracao.txt`) não foram alterados.

## Capturas de origem (locais, não versionadas)

`<RAIZ>/.workspace/tmp/ns001-studio-bella/CAP-01..CAP-10-*-1080x1920.jpg` — capturas reais
do painel demonstrativo Studio Bella (agenda: painel, semana, dia, mês, filtros, busca,
detalhes, pendente, confirmado), com origem/licença registradas nos asset-manifests.

## Manifestos, hashes e validações

- `entrega-v2/index.json` (`overallStatus: completed`, 3/3 perfis) + `entrega-v2/<perfil>/delivery-manifest.json`.
- `entrega-v2/checksums.sha256` (9 arquivos: MP4/SRT/TXT por perfil).
- Inspeção independente (`build_video.validate_mp4`): 1 stream de vídeo, 0 de áudio,
  h264 1080×1920@30, yuv420p/tv, 47,0 s — nos três perfis.
- SRT validado nos três perfis (`srt_validate.validate_srt_text`, duração 47,0 s).
- Player verificado em navegador: 3 vídeos carregam (47 s, 1080×1920), seek e legendas
  sincronizadas funcionando (fallback JS + track nativo; legendas também queimadas no vídeo).
- Registro da validação: `.workspace/logs/ns001-studio-bella-v2/validacao-final.json` (local).
- Pedido versionado: [pedido-editorial-v2.video-request.json](pedido-editorial-v2.video-request.json).

## Pendências reais

1. Revisão humana do titular pendente — esta entrega não é campanha aprovada para publicação.
2. Verificação visual das capturas e dos frames pelo titular: o agente desta sessão não
   possui entrada de imagem; a qualidade visual não foi declarada aprovada, apenas a
   conformidade técnica (ffprobe/SRT/manifestos).
3. Commit/push das alterações versionadas (pedido v2, SRT/TXT v2, este índice e a correção
   em `tools/render_local.py`) aguardam autorização; nada foi mesclado, publicado ou agendado.
4. Mídias (MP4/JPG) não versionadas por política do repositório; existem apenas nesta estação.
5. CTA/destino/bio/UTM por canal: pendência herdada da v1 (decisão 7), fora do escopo desta revisão.