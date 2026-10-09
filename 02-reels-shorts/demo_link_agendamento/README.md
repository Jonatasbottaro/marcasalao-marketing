# Campanha: Demonstração Link de Agendamento

## Objetivo
Apresentar a jornada do profissional para gerar, copiar e compartilhar o link/QR de agendamento.

## Entregáveis
- `demo_link_agendamento_sem_audio.mp4` — vídeo final sem áudio, legendas queimadas.
- `../04-legendas/roteiro_demo_link_agendamento.md` — roteiro de narração por cena.
- `../04-legendas/roteiro_demo_link_agendamento.srt` — legendas sincronizadas.

## Política de produção
- Vídeo **sem áudio**, sem preservar áudio original, sem TTS/música no editor.
- Legendas visíveis e sincronizadas.
- Texto de narração separado para geração de áudio externa.
- Material de demonstração, não campanha final aprovada até validação.

## Como reproduzir
```bash
ffmpeg -i video_original.mp4 \
  -vf "subtitles=../04-legendas/roteiro_demo_link_agendamento.srt:force_style='Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=60'" \
  -an -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p demo_link_agendamento_sem_audio.mp4
```

## Próximos passos
- Validar tempos do SRT com o vídeo final.
- Gerar áudio de narração externamente a partir do roteiro.
- Criar versão clean sem legendas, se necessário.
