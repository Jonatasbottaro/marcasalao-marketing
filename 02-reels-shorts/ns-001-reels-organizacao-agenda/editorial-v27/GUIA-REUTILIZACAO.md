# Guia operacional de reutilização — composição editorial v2.7

Componentes: `tools/editorial_compose.py` (motor) + manifesto `*.editorial.json` (configuração).
Contrato de saída: VideoRequest v1 canônico (`platform/schemas/video-request.schema.json`), renderizado por `tools/produce_video.py`. Nada aqui substitui o Video Studio.

Referência completa: `campanha-v27.editorial.json` (Marca Salão) e `tools/tests/fixtures/editorial/marca-exemplo.editorial.json` (fixture fictícia).

## 1. Fornecer a identidade de uma marca

Preencha `brand` no manifesto: `primaryColor`, `backgroundColor`, `textColor`, `mutedColor` (hex), `functionalColors` por status (`text` + `surface`) e `logo` (`path` + `sha256`). Registre a proveniência da cor primária (`primaryColorProvenance`) — se a marca não fixa hex oficial, derive do logotipo/aprovações e declare. Tokens de cor usáveis nas cenas: `primary`, `text`, `muted`, `func:Nome`, `funcSurface:Nome`.

## 2. Adicionar capturas reais

Cadastre cada captura em `evidence[]`: `id`, `path` (relativo à raiz), `sha256`, `kind`, `source` (como foi obtida) e `regions` nomeadas (`x,y,w,h` em pixels da fonte). O arquivo deve estar dentro de um diretório listado em `assetScopes`. Versione a captura junto do manifesto (como em `editorial-v27/fontes/`) para a campanha ser reproduzível em qualquer estação.

## 3. Registrar informações verificadas

Liste em `evidence[].values` todo valor que pode aparecer em destaque (horários, serviços, status, períodos). Cada `highlight` e cada estado de `status-sequence` referencia `evidenceId` + `region` + `value`; o validador reprova valor ausente da lista (`HIGHLIGHT_VALUE_UNVERIFIED`), região inexistente ou hash divergente. Confira os valores contra a captura (OCR/snapshot) antes de declarar — nunca invente dados.

## 4. Selecionar um template

Escolha `component` por cena: `product-context` (interface real + título), `product-proof` (recorte real + destaques verificados; aceite `parts[]` com janelas `startMs/endMs`), `status-sequence` (2–3 estados com cartão real por estado), `brand-endcard` (`approved-art` ou gerado com logo + `brandName` + `ctaText`) e `static-art` (arte aprovada intacta). Layout em pixels do canvas; `motionIntent` do pedido final permanece `none` — o movimento (revelação, deriva, fades) é assado na mídia pelo motor.

## 5. Definir o perfil de saída

Declare `safeAreas` por perfil (frações de topo/base/laterais + `basis` e `note` honestos sobre a referência). O motor reprova layout crítico fora da área útil (`SAFE_AREA_VIOLATION`). No VideoRequest final, liste os perfis permitidos pelo manifesto do projeto (ex.: `platform/examples/projects/marca-salao-social.project.json`). `captionBand` opcional cria faixa de marca sob a banda de legendas do renderizador (y 1550–1650 em 1080×1920) para contraste.

## 6. Gerar a prévia

```bash
python tools/editorial_compose.py --manifest <manifesto> --root <RAIZ> \
  --output-dir <RAIZ>/.workspace/tmp/<tarefa>/media \
  --safe-area-preview --preview-frames-dir <dir-com-frames-png> --json
```

Inspecione os frames (OCR ou visual) e as prévias de área segura. A sobreposição vermelha é somente QC — nunca entra na mídia. Para a prévia da montagem completa com legendas, use `produce_video.render_assembly_preview` (escala 0.5–1.0) antes do render final.

## 7. Renderizar

Escreva o `*.video-request.json` (mídias geradas em `.workspace/tmp/…`, tipos `video`/`image`, `durationMs` = duração da mídia, `motionIntent: none`, framing zoom 100) e rode:

```bash
python tools/produce_video.py --input <pedido> --root <RAIZ> \
  --output-dir <RAIZ>/.workspace/tmp/<tarefa>/entrega --json
```

Exigências do ambiente: FFmpeg/FFprobe no PATH ou em `<RAIZ>/.workspace/tools/ffmpeg/`; build da platform (`platform/dist`) na raiz usada. Saída: 1 MP4 + SRT + narração TXT + manifestos por perfil, sempre sem áudio.

## 8. Revisar a entrega

Confira por FFprobe (geometria, fps, duração, codec, zero áudio), checksums, correlação frames×cenas e legibilidade em 360×640 (OCR serve de proxy objetivo; a aprovação editorial humana é do titular). Gere player HTML + ZIP portátil com os MP4, SRT, narração e relatórios QC. Não publique nem agende sem autorização explícita.

## 9. Manter clientes isolados

`assetScopes` limita toda mídia ao diretório do cliente/campanha; evidência ou asset fora do escopo reprova (`ASSET_SCOPE_VIOLATION`). `clientId`/`campaignId` próprios, paleta própria, fontes próprias. Nunca reaproveite capturas, valores ou artes de outro cliente. A fixture `marca-exemplo` demonstra o fluxo completo sem tocar material real.

## Reprodutibilidade

Mesmo manifesto + mesmas fontes = mesmos bytes (teste `test_editorial_compose_render`). Fontes tipográficas resolvidas em runtime (Arial Bold do sistema ou fallback DejaVu); nenhuma dependência nova além de FFmpeg. Arquivos permanentes no Git; mídias e logs em `.workspace/`, regeneráveis.