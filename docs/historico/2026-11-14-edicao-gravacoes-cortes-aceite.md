# Aceite — Edição de gravações e cortes por cena no Video Studio (14/11/2026)

Registro da prova de aceite da rodada `recording-cuts-v1`, com dados fictícios.
Branch técnica: `codex/recording-cuts-v1`, a partir do checkpoint
`566c05ac890362c030059501ff26a72aa42e7700` (main após o merge multiformato `bff2e46`).
Este documento registra evidência observada; não é aprovação editorial nem autoriza publicação.

## Escopo provado

- Importação de gravação MP4 H.264 pelo navegador (blocos de até 4 MiB, limite de 256 MiB,
  FFprobe, promoção conjunta arquivo + registro, versões preservadas).
- Corte por cena no `VideoRequest v1` (`sourceStartMs`), com player mudo, Marcar entrada/saída,
  campos editáveis, Reproduzir trecho, erro junto da cena, duplicação e reordenação.
- Prévia sem FFmpeg distinguindo janela da fonte e posição na montagem.
- Render real com seek preciso entre keyframes nas geometrias 9:16 e 16:9, zero áudio,
  SRT + narração TXT, `sourceCuts` no manifesto/relatório.
- Revisão por modalidade/perfil/versão com `draft_outdated` por mudança de início (vídeo e Motion),
  reexportação de um perfil com hashes previstos, falha controlada preservando a última entrega.
- ZIP com referência aos cortes e hashes conferidos; recuperação após reinício.

## Fixture

`make_proof_assets.write_recording_mp4`: 12 s, três trechos de 4 s com cores sólidas
identificáveis — A vermelho (220,40,40), B verde (40,190,60), C azul (50,80,220) — e faixas
brancas distintas (1/2/3). Codificação em passada única com GOP de 90 quadros (3 s):
keyframes em 0/3/6/9 s, **nunca** nas fronteiras de trecho (4/8 s). Um render que começasse
no instante 0 ou no keyframe anterior produziria a cor errada.

- SHA-256 da fonte: `078b867f3a343c4d66755239fee56f68f8fc30ac97887d5bf316907b02ed7cd4`
- Duração no player do navegador: **12 s**; duração comprovada no arquivo exportado: **7,6 s**.

## Cortes usados (trabalho fictício `rc-aceite-ms`, Chromium real)

| Cena | Mídia | Início na fonte | Fim na fonte | Duração | Posição na montagem |
| --- | --- | --- | --- | --- | --- |
| cena-1 | gravação | 4200 ms | 6600 ms | 2400 ms | 0 → 2400 ms |
| cena-2 | cartela (imagem) | — | — | 2000 ms | 2400 → 4400 ms |
| cena-3 | gravação | 8300 ms | 10000 ms | 1700 ms | 4400 → 6100 ms |
| cena-4 | gravação (B reaproveitado) | 4200 ms | 5700 ms | 1500 ms | 6100 → 7600 ms |

Dois trechos começam depois de zero em cenas diferentes (4,2 s e 8,3 s); o trecho B é
reaproveitado em outra posição; uma imagem estática entra na sequência.

## Medidas FFprobe dos MP4 promovidos (primeira exportação)

| Perfil | Geometria | Codec | FPS | Duração | Áudio | SHA-256 (prefixo) |
| --- | --- | --- | --- | --- | --- | --- |
| instagram-reels-video | 1080×1920 | h264 | 30/1 | 7,6 s | 0 faixas | `87f6879a80b7d4ed` |
| youtube-video-horizontal | 1920×1080 | h264 | 30/1 | 7,6 s | 0 faixas | `4e5662230bbc9978` |

## Verificação de quadros (automatizada, por cor do trecho)

Amostra em (10% largura, 92% altura) no vertical e (50%, 92%) no horizontal (conteúdo
centralizado do pillarbox), longe das faixas brancas:

| Tempo da montagem | Esperado | reels | horizontal |
| --- | --- | --- | --- |
| 0,1 s | B (verde) | B | B |
| 5,0 s | C (azul) | C | C |
| 6,8 s | B (verde, reaproveitado) | B | B |

O primeiro quadro ser B (e não A/vermelho) prova que o render não começou no instante 0
nem no keyframe de 3 s; o quadro de 5,0 s ser C (e não B) prova que o corte de 8,3 s não
começou no keyframe de 6 s. Quadros preservados em `.workspace/logs/recording-cuts-v1/browser/`.
Título/legenda/SRT alinhados à montagem (SRT conferido: blocos 0→2,4 / 2,4→4,4 / 4,4→6,1 / 6,1→7,6 s).

## Reexportação com apenas o início alterado (4200 → 4600 ms)

- MP4 do reels: **mudou** (`87f6879a…` → novo hash); primeiro quadro continua B (4,6 s ainda é trecho B).
- SRT do reels: **igual** (`e4430e944a77df58…`); narração TXT: **igual** (`bcc4a13c3ee25bbf…`).
- Fonte: **igual** (`078b867f…`).
- Perfil fora da reexportação (horizontal): video/SRT/TXT **intactos** (`4e566223…` / `e4430e94…` / `2b59fad6…`).
- Revisão: ambas as peças de vídeo foram a `draft_outdated` com a mudança; carrossel independente
  não foi afetado; Motion exportado para a mesma cena também foi a `draft_outdated`.

Hashes completos: `.workspace/logs/recording-cuts-v1/hashes-before.json` e `hashes-after.json`.

## Falha controlada

cena-3 com duração 4000 ms (8300 + 4000 = 12300 > 12000 disponíveis):

- Erro estável: `SOURCE_CUT_OUT_OF_RANGE: cena-3 pede fonte [8300ms -> 12300ms], asset 'asset-v-0ff1edec46' tem 12.000s disponiveis`.
- Erro exibido junto da cena no editor ("Trecho ultrapassa a fonte…").
- Última entrega válida preservada (hashes idênticos; `index.json` com `lastAttempt.status=failed`
  e `lastValidDelivery` presente).

## ZIP final

- `rc-aceite-ms-pkg-cb8fd4cfad` · **231268 bytes** ·
  SHA-256 `6bebfdb6a95b735eba137dd4123118e21183ae51811235ce442a287806971381` · 9 entradas
  (2 MP4s + 2 SRTs + 2 TXTs + ficha editorial JSON/TXT + manifesto).
- `sourceCuts` por peça no `package-manifest.json` (cena-1 com 4600→7000 ms após a reexportação).
- Manifesto conferido contra os bytes empacotados: 0 divergências; `testzip()` OK.
- Download pelo navegador: HTTP 200, assinatura `PK`, `Content-Disposition: attachment`.

## Reinício

Servidor reiniciado após salvar: cortes recuperados (`[4200, null, 8300, 4200]`), perfis e
estado de revisão preservados; pacote ZIP continua disponível com o mesmo hash.

## Limitações observadas

- "Reproduzir trecho" pausa com a granularidade do `timeupdate` (~0,25 s); o corte exportado é exato.
- Após reordenar, o player recriado mostra "duração desconhecida" até `loadedmetadata`; o erro de
  trecho só aparece quando a duração da fonte é conhecida.
- Motion permanece restrito a 9:16 (recorte da rodada multiformato, preservado).
- A importação de vídeo aceita apenas MP4 H.264 (outros codecs/conteiners são rejeitados com mensagem).

## Evidências

- Capturas (8) + quadros extraídos (9): `.workspace/logs/recording-cuts-v1/browser/`
  (Playwright MCP só grava em pasta de usuário; arquivos movidos imediatamente para dentro da raiz).
- Roteiro da prova: `.workspace/logs/recording-cuts-v1/browser-e2e.json`.
- Suítes: `.workspace/logs/recording-cuts-v1/tests-round3.log` (15 testes OK),
  `python-suite-full.log` (suíte completa com `REQUIRE_RENDER=1`),
  `ci-proof-local.log` (prova HTTP `tools/ci_recording_cuts_proof.py`).
- CI pós-merge: registrado em `docs/contexto/ESTADO-ATUAL.md` após a integração.