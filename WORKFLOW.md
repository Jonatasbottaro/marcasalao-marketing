# Workflow de Marketing Marca Salão

## Ferramentas
- **Antigravity AI Agent**: Edição conversacional automatizada, raciocínio de cortes e renderização
- **HyperFrames (HeyGen)**: Renderização gráfica determinística em HTML/CSS/GSAP para overlays e motion graphics
- **video-use**: Pipeline de cortes cirúrgicos, fades de áudio de 30ms anti-pop e legendagem
- **FFmpeg**: Automação e composição de vídeo, áudio e legendas
- **CapCut / Drift**: Editores manuais de apoio (opcionais)

## Fluxo completo

### 1. Captura
- Login demo: demo.gestor@example.com / Demo@123456
- Navegue nas seções e capture telas via browser

### 2. Artes
- Salve PNG 1080x1920 em `01-insta-stories/`
- Adicione README por pasta

### 3. Legendas
- Escreva textos curtos em `04-legendas/`
- Formato: título + 3-5 bullets + CTA

### 4. Edição
#### CapCut
- Importe imagens + áudio
- Adicione texto dinâmico
- Exporte 1080x1920, 30fps

#### Drift
- Importe mídia via UI ou MCP Agent
- Use Look Templates para consistência
- Exporte vertical e horizontal

#### FFmpeg
- Automação de lote
- Adição de áudio e sobreposição de texto

### 5. Publicação
- Instagram/Reels: `02-reels-shorts/`
- YouTube/PDF: `03-youtube-pdf/`
- GitHub Releases para distribuição

## Checklist
- [ ] Capturas sem dados sensíveis
- [ ] Legendas revisadas
- [ ] Áudio gravado
- [ ] Vídeo exportado
- [ ] Commit + push no repo
