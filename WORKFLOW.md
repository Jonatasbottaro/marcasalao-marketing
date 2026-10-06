# Workflow de Marketing Marca Salão

## Ferramentas
- **Antigravity AI Agent**: Edição conversacional automatizada, raciocínio de cortes e renderização
- **HyperFrames (HeyGen)**: Renderização gráfica determinística em HTML/CSS/GSAP para overlays e motion graphics
- **video-use**: Pipeline de cortes cirúrgicos, legendagem (recursos de áudio não usados neste projeto)
- **FFmpeg**: Automação e composição de vídeo e legendas, sem áudio
- **CapCut / Drift**: Editores manuais de apoio (opcionais)

## Regra de produção: vídeo sem áudio

- Gerar vídeos com legendas visíveis e sincronizadas às cenas.
- Não preservar o áudio original das gravações.
- Não gerar nem inserir narração, música, efeitos sonoros ou qualquer outro áudio no editor.
- Entregar o texto de narração separado em `04-legendas/`, em português brasileiro, organizado por cenas e tempos, pronto para copiar para uma ferramenta externa.
- Entregar também o arquivo `.srt` correspondente às legendas do vídeo.
- O usuário gera o áudio fora do editor de vídeo; essa etapa não é requisito para entregar o vídeo legendado.
- Preferir exportação sem faixa de áudio; não confundir faixa silenciosa com narração gerada.
- Só mudar essa política mediante pedido explícito do usuário.
- Os vídeos existentes de demonstração/teste não devem ser apresentados como campanhas finais aprovadas.

### Aplicação às ferramentas

Esta regra específica do Marca Salão orienta o uso das skills e templates genéricos: não seguir etapas de TTS, música ou preservação de áudio nesses fluxos. Nas composições, manter vídeos mudos e não adicionar elementos de áudio. Na exportação com FFmpeg, mapear somente vídeo e usar `-an`.

### Verificação da entrega

- Conferir as legendas, legibilidade e correspondência com as cenas.
- Conferir a duração do vídeo, do SRT e dos tempos indicados no roteiro.
- Conferir com `ffprobe` se há faixas de áudio; a exportação preferida não contém nenhuma.
- Entregar vídeo legendado + SRT + texto de narração separado, sem gerar áudio.

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
- Entregue `.srt` sincronizado e texto de narração separado por cenas e tempos, para geração de áudio fora do editor

### 4. Edição
#### CapCut
- Importe imagens e vídeos, sem áudio original e sem adicionar áudio
- Adicione texto dinâmico
- Exporte 1080x1920, 30fps

#### Drift
- Importe mídia via UI ou MCP Agent
- Use Look Templates para consistência
- Exporte vertical e horizontal, sem áudio

#### FFmpeg
- Automação de lote
- Sobreposição de texto e exportação sem áudio (`-an`)

### 5. Publicação
- Instagram/Reels: `02-reels-shorts/`
- YouTube/PDF: `03-youtube-pdf/`
- GitHub Releases para distribuição

## Checklist
- [ ] Capturas sem dados sensíveis
- [ ] Legendas revisadas
- [ ] Texto de narração separado e pronto para ferramenta externa
- [ ] SRT sincronizado com as cenas
- [ ] Vídeo sem áudio original, narração, música ou efeitos
- [ ] Vídeo exportado
- [ ] Commit + push no repo
