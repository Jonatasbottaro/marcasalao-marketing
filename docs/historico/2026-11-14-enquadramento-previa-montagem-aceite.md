# Aceite — Enquadramento por cena/destino e prévia da montagem (14/11/2026)

Registro objetivo da entrega local da fatia **enquadramento por cena e por destino, com prévia da montagem no Video Studio**, executada na branch técnica `codex/scene-framing-preview-v1` (sobre `7036d64444dd23e0f2a54567125c8918a95b5e15`), com dados fictícios sob `<RAIZ>`.

## Escopo comprovado

1. **Contrato no `VideoRequest v1` (`framingByProfile`)**:
   - Campo opcional por cena (`centerX`, `centerY` em `[0, 1]`, origem no canto superior esquerdo; `zoomPercent` inteiro em `[100, 300]`), indexado por perfil de vídeo do catálogo (`mediaKind: "video"`).
   - Cena sem ajuste para o perfil em execução usa **Ajustar** (mídia inteira centralizada com preenchimento nas bordas); pedidos legados e `validateComposition` permanecem inalterados.
   - Perfis podem sair de `request.profiles` e retornar mantendo os ajustes salvos por cena.
   - `tools/produce_video.py --plan-only --json` exibe a intenção de enquadramento junto dos tempos de fonte (`sourceStartMs`/`sourceEndMs`) e da montagem (`startMs`/`endMs`), sem FFmpeg, leitura de mídia nem escrita em disco.
   - `tools/render_local.py` (`resolve_scene_framing`) resolve o recorte em pixels pares antes de `slow-zoom`, Motion `9:16`, títulos e legendas, e rejeita `Preencher` em mídia com rotação (`!= 0`) ou SAR não quadrado com `FRAMING_MEDIA_METADATA_UNSUPPORTED`, oferecendo retorno para **Ajustar**.

2. **Video Studio (`tools/studio/app.js` + `tools/video_studio.py`)**:
   - Seletor de perfil ativo (`#v-active-profile`), faixa navegável da montagem (`#v-assembly-timeline`) com ordem, tempos e clique para selecionar cena e saltar o player para o início dela.
   - Botões **Ajustar** (`#v-frame-mode-fit`), **Preencher** (`#v-frame-mode-fill`) e **Desfazer ajuste desta cena** (`#v-frame-reset-btn`), arraste no quadro da fonte (`#v-frame-source-canvas` carregando o quadro da gravação em `sourceStartMs`), prévia do quadro resultante (`#v-frame-dest-canvas`), entradas numéricas/deslizador (`#v-frame-center-x`, `#v-frame-center-y`, `#v-frame-zoom`, `#v-frame-zoom-range`) e diagnóstico em pixels do adaptador (`POST /api/video/frame-info`).
   - Botão **Gerar prévia da montagem** (`POST /api/video/preview-render`, `GET /api/video/preview-status`) para um perfil por vez, em resolução menor par, com player mudo (`#v-preview-player`) com seek por HTTP Range (`206`), cache limitado a `<= 4` MP4s por trabalho em `.workspace/studio/works/<id>/previews/`, fingerprint do perfil e aviso quando a edição muda durante ou após a geração (`Prévia da versão anterior`).

3. **Revisão localizada, reexportação e pacote ZIP (`tools/studio_review.py` + `tools/delivery_package.py`)**:
   - Versão efetiva por perfil considera apenas seu próprio ajuste (`ausente ≡ Ajustar`). Alterar o enquadramento do Reels marca `video:instagram-reels-video` e `motion:instagram-reels-video` como `draft_outdated`, mantendo `approved` o YouTube horizontal e o carrossel independente.
   - Reexportar apenas o Reels altera o MP4 escolhido e preserva os hashes da mídia original, `.srt`, `.txt` e do YouTube horizontal.
   - Falha controlada na reexportação preserva a entrega anterior válida e o histórico de decisões; `package-manifest.json` do ZIP registra `sourceCuts` e `framings` com hashes conferidos contra os bytes finais.

## Medidas e hashes observados

### Suítes automatizadas

- **Platform** (`npm --prefix platform run build`, `typecheck`, `test`): `994` testes, `994` aprovados, `0` falhas, `0` ignorados.
- **Suíte Python direcionada** (`REQUIRE_RENDER=1 python -m unittest tools/tests/test_scene_framing_preview.py -v`): `4` testes aprovados em `123.990s` (cobrem contrato legado/inválido, metadados com rotação `90°`, troca de mídia/remoção e restauração de perfil, cache `<= 4`, corrida de edição durante prévia, pixels de quadro, reexportação localizada, recuperação após falha e manifesto ZIP).
- **Suíte Python completa** (`REQUIRE_RENDER=1 python -m unittest discover -s tools/tests -v`): `229` testes aprovados em `1841.227s` (`OK`, `0` falhas, `0` erros, `0` ignorados; log em `.workspace/logs/scene-framing-preview-v1/python-suite-full.log`).

### Prova HTTP de CI (`tools/ci_scene_framing_preview_proof.py --port 8799`)

Executada contra o servidor real do Studio com gravação fictícia dividida `1920x1080` (`RED` à esquerda / `BLUE` à direita, `10s`), cartela PNG estática e gravação rotacionada `90°`:

- **Tempos observados**:
  - Prévia `instagram-reels-video`: `2.223s` (HTTP Range `206`, `256` bytes no intervalo `bytes=128-383`)
  - Prévia `youtube-video-horizontal`: `1.947s` (HTTP Range `206`)
  - Exportação conjunta Vídeo (Reels + YouTube): `5.474s`
  - Exportação Motion `9:16`: `4.521s`
  - Exportação Carrossel `1:1`: `1.867s`
  - Reexportação localizada apenas do Reels: `3.443s`
- **FFprobe dos MP4s promovidos**:
  - `instagram-reels-video`: `1080x1920`, `30/1` fps, H.264, `0` faixas de áudio
  - `youtube-video-horizontal`: `1920x1080`, `30/1` fps, H.264, `0` faixas de áudio
- **Verificação automatizada de área visível por perfil** (prévia vs MP4 final, falhando quando aplicado ao destino errado):
  - Reels direita (`centerX=0.82, zoomPercent=150`): prévia `left=BLUE, right=BLUE` ≡ MP4 inicial `left=BLUE, right=BLUE`
  - YouTube (`Ajustar`): prévia `left=RED, right=BLUE` ≡ MP4 `left=RED, right=BLUE`
  - Reels esquerda após edição (`centerX=0.18, zoomPercent=150`): MP4 reexportado `left=RED, right=RED`
- **Hashes SHA-256 observados**:
  - Gravação original preservada: `2f7112eb24dc17c6e9f86593c831794dc8e863eb7759997593c2ca29fd5abd14`
  - Reels MP4 antes: `98fad894fa4ac49c8e6b30cbc1f46f0ddc705fbd18052a761e21ed02b12ae1ca`
  - Reels MP4 depois da reexportação localizada: `1bc58a668f79c272fd9ba719b56d4cc06ba557219bb1a942b023e692e8fd7d84`
  - YouTube MP4 preservado antes e depois: `3514f0ff8f468e14f2985ce05310fc77a0a8a1267f559d848d16ba0e8b47f35f`
  - Pacote ZIP (`510233` bytes): `aa4fe4eb905742e48c1cbe1c07d45aa29e3523f9d10c4262d8a581f222ae386e`
  - Falha controlada posterior (`durationMs=9000`) manteve intactos os hashes da última entrega válida.

### Aceite no Chromium real (CDP sobre `tools/video_studio.py`)

Evidência registrada em `<RAIZ>/.workspace/logs/scene-framing-preview-v1/browser-e2e.json` (7 capturas `01-reels-framing-editor.png` a `07-review-zip-complete.png` e 5 quadros comparados em `t=0.75s` sob `browser/frames/`):

- **Tempos observados no navegador**: prévia Reels `3139 ms`, prévia YouTube `2786 ms`, exportação conjunta Vídeo `6566 ms`, reexportação isolada Reels `4355 ms`.
- **Faixa navegável (`#v-assembly-timeline`)**: salto para a cena 2 posicionou `#v-preview-player.currentTime` em `2.2s` e retornou à cena 1 (`0s`).
- **Comparação visual de quadros (`t=0.75s`)**: `preview-reels-t075.png` e `final-reels-initial-t075.png` idênticos em área azul (`BLUE`/`BLUE`) com título `FOCO DIREITA REELS` no topo e legenda `Detalhe direita no Reels` na base; `preview-yt-t075.png` e `final-yt-t075.png` idênticos em quadro `16:9` dividido `RED`/`BLUE` com título e legenda preservados; `final-reels-reexported-t075.png` alterado apenas para a área esquerda (`RED`/`RED`).
- **Hashes no fluxo do navegador**: Reels MP4 `79fb373b97695836ce6768a63f23ae05d89a666fa8a281dc50972c51d727a04d` → `fffe1d67da6ab53b162e5e371af5cf3f14e45c2e84c6363ff26a657187bee875`; `reelsSrt` (`081fb7b1f23c0b3c71708a17e5c4339b089b146efbfae65fceee38ae4cda3317`), `reelsTxt` (`272c6dfffb26f7491f2163cf724b516989937d3710857981983d4c1caa6a7fad`) e `ytMp4` (`924613377a101dd80ec09831dc5ba920c34484c9c70758413031599504ad8250`) preservados idênticos; ZIP baixado com status `200` e `657104` bytes.

## Limitações reproduzidas e escopo preservado

- Entrega estritamente local com dados fictícios, MP4 sem faixa de áudio (`audioStreams: 0`), SRT UTF-8 e narração TXT separada.
- Mídias com rotação de stream (`!= 0`, testado com `90°`) ou SAR não quadrado são bloqueadas no modo **Preencher** (`FRAMING_MEDIA_METADATA_UNSUPPORTED`), exigindo retorno para **Ajustar** ou normalização prévia da fonte.
- Motion segue restrito ao formato vertical `9:16` com coordenadas relativas ao quadro final enquadrado.
- Observação visual na aba **Revisão & Entrega** (capturas `06`/`07` em `1440×960`): o player `<video>` embutido nos cartões da peça `1920×1080` renderiza sem limitação de largura máxima no cartão, gerando rolagem horizontal visual na aba Revisão sem impedir aprovações ou geração do ZIP; na aba **Vídeos**, `#v-preview-player` permanece contido.
- Nenhuma publicação automática, agendamento ou alteração da API pública mínima (`validateComposition`).
