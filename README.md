# Marca Salão Marketing

Repositório de marketing do Marca Salão, com fluxos também organizados para a Multitrack Hub e um núcleo reutilizável de produção de conteúdo em evolução.

## Contexto e continuidade

Comece por [docs/contexto/README.md](docs/contexto/README.md). O [estado atual](docs/contexto/ESTADO-ATUAL.md) diferencia o código integrado na main, as alterações em revisão e as pendências editoriais. As [próximas etapas](docs/contexto/PROXIMOS-PASSOS.md) e o [handoff](docs/contexto/HANDOFF.md) orientam a retomada entre agentes e computadores.

A arquitetura e os comandos do núcleo ficam em [platform/README.md](platform/README.md). As decisões de arquitetura são registros históricos; não substituem a verificação do código e das PRs.

## Estrutura
- `00-briefings/` - Briefings de campanha: dor, impacto, evidência e limites de promessa antes de produzir
- `01-insta-stories/` - Cards 1080x1920 para Instagram/WhatsApp com guia CapCut
- `02-reels-shorts/` - Vídeos verticais para Reels/Shorts/TikTok
- `02-hooks/` - Hooks em rascunho por campanha, derivados dos briefings
- `03-youtube-pdf/` - PDFs e apresentações para YouTube/Site
- `03-roteiros/` - Roteiros por campanha: cenas, textos de tela e narração em rascunho
- `04-legendas/` - Legendas, roteiros e scripts de áudio
- `marcas/` - Materiais, configurações e integrações específicas de Marca Salão e Multitrack Hub
- `platform/` - Contratos, schemas, validação, relatórios, CLIs e testes do núcleo reutilizável
- `docs/contexto/` - Contexto compartilhado, estado atual, próximos passos e procedimento de retomada

## Ferramentas
- CapCut (mobile/desktop)
- Drift - https://cutwire.org/drift
- FFmpeg

## Demo

Acesse a demonstração:
https://marcasalao.com.br/gestor

As credenciais de demonstração não são mantidas neste repositório.
Solicite um acesso de demonstração ao responsável pelo projeto.

## Padrão de entrega
Vídeos sem áudio, com legendas nas cenas, arquivo SRT e texto de narração separado para geração de áudio em ferramenta externa. Não preservar o áudio original nem gerar áudio no editor. Vídeos de teste não são campanhas finais aprovadas.

## Produzir o primeiro vídeo (entrada única)

Descreva as cenas em um JSON, confira a prévia e exporte para os perfis escolhidos. O mesmo pedido gera `instagram-reels-video`, `facebook-reels-video` e `youtube-shorts` a partir da mesma fonte de cenas e mídia. Guia completo em [tools/produce/README.md](tools/produce/README.md).

```bash
cd platform && npm ci && npm run build && cd ..   # FFmpeg/FFprobe no PATH
python tools/make_request_media.py --input tools/produce/examples/marca-salao-social-reel.video-request.json
python tools/produce_video.py --input tools/produce/examples/marca-salao-social-reel.video-request.json --plan-only --json
python tools/produce_video.py --input tools/produce/examples/marca-salao-social-reel.video-request.json --output-dir .workspace/archives/primeiro-video --json
```

Cada perfil entrega MP4 sem áudio, SRT, narração em TXT, pacote canônico, inventário de mídia e `delivery-manifest.json`; o `index.json` reúne o estado por perfil. Os casos gerados são rascunhos editoriais, não campanhas aprovadas.

### Painel local (Video Studio)

Para criar, revisar e exportar pelo navegador, abra o painel local:

```bash
python tools/video_studio.py --port 8765
# abra http://127.0.0.1:8765
```

No painel: selecione o `ProjectManifest`, carregue os perfis (Reels/Shorts 9:16@30), carregue um exemplo (Marca Salão ou Multitrack Hub), cadastre/escaneie mídias de uma pasta em `.workspace/`, edite as cenas (duração, legenda, título, narração), confira a **prévia sem FFmpeg** e **exporte**. Ao terminar, assista ao MP4 no painel e baixe MP4/SRT/TXT; reexporte apenas um perfil após corrigir uma cena. As entregas ficam em `.workspace/archives/video-studio/<pedido>/` (um subdiretório por perfil + `index.json`). O painel escuta só em `127.0.0.1`, valida Host/Origin e confina tudo à raiz; uma reexportação que falha preserva a última entrega válida. Guia em [tools/produce/README.md](tools/produce/README.md).

### Carrosséis (R003)

O mesmo painel tem a aba **Carrosséis**: escolha o projeto, monte os cards (capa, conteúdo, fechamento com CTA), confira a ordem, exporte os JPEGs 1080×1080 e baixe o ZIP. Pela CLI:

```bash
python tools/make_request_media.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json
python tools/produce_carousel.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json --plan-only --json
python tools/produce_carousel.py --input tools/produce/examples/marca-salao-carousel.carousel-request.json --output-dir .workspace/archives/carrossel --json
```

A entrega traz JPEGs numerados (`01-capa.jpg`, …), `carousel.zip` na mesma ordem e `carousel-manifest.json` (id, dimensões, caminhos, tamanhos, SHA-256). Remover um card e reexportar reflete a nova ordem no conjunto e no ZIP; uma falha preserva a última entrega válida.

### Motion (contorno animado)

A aba **Motion** do painel destaca uma região da cena com um contorno animado. Caminho mais curto:

```bash
python tools/make_agenda_media.py --output .workspace/tmp/motion-demo/assets/marca-salao/agenda.png
python tools/video_studio.py --port 8765   # aba Motion: carregar exemplo, marcar região, exportar
# ou pela CLI:
python tools/produce_video.py --input tools/produce/examples/marca-salao-motion.video-request.json --motion-plan tools/produce/examples/marca-salao-motion.motion-plan.json --output-dir .workspace/archives/motion --json
```

O plano (`MotionPlan v1`) define região relativa, cor, espessura e intervalo por cena; a prévia (`--plan-only`) resolve os tempos absolutos sem FFmpeg. O contorno é aplicado antes dos títulos/legenda, com entrada/saida suaves; o MP4 sai sem áudio, com SRT e narração. O plano canônico vai para o manifesto com hash.

## Workflow
Ver `WORKFLOW.md` para passo a passo completo e `AGENTS.md` para as regras do projeto.

## Contribuição
1. Adicione artes nas pastas correspondentes
2. Atualize legendas em `04-legendas/`
3. Commit + push

## Releases
Use GitHub Releases para distribuir pacotes de vídeo completos.

## Hermes e Postiz

[Documentação do Hermes](docs/hermes/README.md): prompts separados para Marca Salão e Multitrack Hub, conexão validada no Servidor02 e preparação de rascunhos com publicação somente após autorização específica.
