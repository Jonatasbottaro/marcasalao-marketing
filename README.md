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
