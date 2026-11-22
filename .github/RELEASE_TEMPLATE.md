# Campanha Marketing Marca Salão

## 📦 Conteúdo desta release
- **Plataforma**: Instagram / Reels / Shorts / YouTube / Site
- **Ferramentas**: CapCut / Drift / FFmpeg
- **Data**: {{ date }}

## 🎬 Vídeos incluídos
| Arquivo | Descrição | Duração | Formato |
|---------|-----------|---------|---------|
| `01_dashboard.mp4` | Dashboard Gestor | 5s | 1080x1920 |
| `02_servicos.mp4` | Gerenciar Serviços | 5s | 1080x1920 |
| `...` | ... | ... | ... |

## 📸 Artes
- `01-insta-stories/` - Cards 1080x1920
- `03-youtube-pdf/` - PDF guia completo

## 📝 Legendas e roteiros
- Ver `04-legendas/` para textos de narração

## 🛠️ Como editar
1. **CapCut**: Importe imagens de `01-insta-stories/` e exporte 1080x1920 **sem adicionar áudio** (a entrega padrão é muda; a locução é gerada fora do editor a partir de `04-legendas/*_narracao.txt`)
2. **Drift**: Importe via UI ou MCP Agent Access
3. **FFmpeg**: Automação em lote via scripts, mapeando somente vídeo (`-an`)

## 🔗 Links úteis
- Portal: https://marcasalao.com.br
- Demonstração: https://marcasalao.com.br/gestor (credenciais não ficam neste repositório; solicite acesso ao responsável pelo projeto)

## 📋 Checklist
- [ ] Vídeo sem faixa de áudio (conferido com `ffprobe`)
- [ ] `.srt` sincronizado entregue
- [ ] Texto de narração separado em `04-legendas/`
- [ ] Legendas revisadas
- [ ] Vídeos exportados
- [ ] Testado em Instagram/YouTube

## 📌 Notas
Adicione observações sobre a campanha, público-alvo e métricas esperadas.
