# Template de Campanha de Marketing - Marca Salão

Este template padroniza a entrega de vídeos de marketing para garantir reprodutibilidade em diferentes estações.

## Estrutura da campanha
```
02-reels-shorts/<nome_campanha>/
  README.md                  # descrição, objetivo, política, como reproduzir
  <nome_campanha>_sem_audio.mp4    # vídeo final sem áudio com legendas
  assets/                    # imagens, capturas, overlays
  04-legendas/
    <nome_campanha>.md       # roteiro de narração por cena
    <nome_campanha>.srt      # legendas sincronizadas
```

## Checklist de entrega
- [ ] Vídeo sem áudio, legendas visíveis
- [ ] SRT sincronizado
- [ ] Texto de narração separado em português
- [ ] README com instruções de reprodução
- [ ] Commit com mensagem descritiva
- [ ] Release no GitHub com pacotes finais

## Política de áudio
- Não gerar nem preservar áudio no editor.
- Narração gerada externamente a partir do roteiro.
- Exportar com `-an` e verificar com ffprobe.

## Como usar
1. Copiar esta pasta como base
2. Substituir nome da campanha
3. Preencher README, roteiro e SRT
4. Gerar vídeo via FFmpeg/HyperFrames
5. Commit + push + tag de release
