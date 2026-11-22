# Reels / Shorts / TikTok

Vídeos verticais 1080x1920 **sem faixa de áudio**: legendas visíveis sincronizadas (`.srt`)
e texto de narração separado em `04-legendas/`, para geração de áudio em ferramenta externa
(regra permanente em [WORKFLOW.md](../WORKFLOW.md)).

## Estrutura
- `*.mp4` - Vídeos finais prontos para publicação
- `*_raw/` - Cenas brutas e capturas

## Ferramentas suportadas
- CapCut Desktop/Mobile
- Drift - editor open source https://cutwire.org/drift
- FFmpeg - automação via script

## Workflow sugerido
1. Importe cards de `01-insta-stories/`
2. Não adicione áudio: mantenha a narração em texto separado (`04-legendas/*_narracao.txt`)
3. Adicione legendas dinâmicas sincronizadas e exporte o `.srt` correspondente
4. Exporte 1080x1920, 30fps, MP4 sem faixa de áudio (`-an` no FFmpeg)

## Drift
AppImage instalado na estação de edição (caminho local, não versionado; nesta estação
Windows o binário fica fora do repositório e não é referenciado por caminho absoluto aqui)
Use Agent Access MCP para automação
