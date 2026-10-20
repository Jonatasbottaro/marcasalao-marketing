# Marca Salão — Antes de abrir, organize o dia

Data editorial: 20/10/2026, America/Sao_Paulo.
Estado: **RASCUNHO / DRAFT** no Facebook e Instagram. Aguardando avaliação do titular. Nenhuma publicação ou programação autorizada/executada.

## Proposta editorial

Checklist antes do primeiro atendimento: conferir a agenda, alinhar a sequência com a equipe e preparar o espaço/materiais. As duas últimas ações são sugestões de rotina, não funcionalidades automáticas do produto. Não promete gestão de estoque, notificações ou automação de tarefas.

Antes de criar, foram consultados os canais via integrationList e os posts no intervalo 18/10–01/11/2026, incluindo os publicados e os rascunhos. O conteúdo novo não reaproveita os posts anteriores nem altera os rascunhos existentes. Não é um inventário exaustivo fora dessa janela.

## Fontes e identidade

- Site oficial: https://marcasalao.com.br, consultado em 20/10/2026. Confirma o contexto de agendamento e gestão de salões. Números, depoimentos, preços e promessas da landing page NÃO foram usados.
- Agenda por dia/semana/mês e filtro por profissional: funcionalidade registrada por inspeção de código em docs/hermes/2026-10-18/GUIA-COMPLETO.md, seção 9. Não foi realizado novo teste funcional do painel nesta produção.
- Logo original: https://marcasalao.com.br/icons/icon-512x512.png, obtida nesta produção; MS serifado com tesoura, sem redesenho.
- Referências visuais consultadas: apresentação de 18/10 e portfólio de 20/10 da própria marca. Paleta verde-petróleo, menta, branco e neutro claro; layout tipográfico, logo no topo, checklist numerado. Sem tela fictícia, fotografias de clientes ou materiais de outra marca.
- O CTA Instagram segue a orientação aprovada para link na bio; o endereço externo do perfil não foi reauditado nesta tarefa. Reconferir antes da publicação.

## Arquivos

- arte-facebook.png: PNG RGB 1080 × 1080; “Acesse o link da descrição”.
- arte-instagram.png: PNG RGB 1080 × 1080; “Acesse o link na bio”.
- legenda-facebook.txt: URL HTTPS completa e indicação para a descrição.
- legenda-instagram.txt: “Conheça o Marca Salão pelo link na bio do @marcasalao”.
- README.md: registro editorial e de persistência dos rascunhos.

Produção estática com Pillow. Revisão visual da arte e verificação programática das margens dos textos. Sem botões clicáveis simulados, áudio, vídeo ou recursos não verificados.

## Rascunhos confirmados no Postiz

| Rede | Canal permitido | ID do rascunho | Estado relido |
|---|---|---|---|
| Facebook | cmvbegwql0001msbhvdpjy0in | cmvgp7inz000emsbe6qujjl3q | DRAFT; error: null |
| Instagram | cmvbeq3100003msbhihu2dm4z | cmvgp7ipe000fmsbeelmbbssn | DRAFT; error: null |

Prévias:
- Facebook: https://postiz.swnsolucoes.com.br/p/cmvgp7inz000emsbe6qujjl3q?share=true
- Instagram: https://postiz.swnsolucoes.com.br/p/cmvgp7ipe000fmsbeelmbbssn?share=true

Mídias confirmadas por mediaListTool:
- Facebook: 8521ef0e-8c69-478d-be63-e9c4d674dfd3 — https://postiz.swnsolucoes.com.br/uploads/2026/10/20/5dfd499e31c43adc4795a89bb1d9f564.png
- Instagram: a646bb9d-42e7-488c-adbe-219d41f1ef27 — https://postiz.swnsolucoes.com.br/uploads/2026/10/20/9c8f361099db91faec210d7488148e9d6d.png

Schemas Facebook e Instagram consultados antes da criação. Upload oficial CLI, um por arte. Uma única chamada MCP integrationSchedulePostTool criou dois registros com type: draft, shortLink: false, post_type: post, sem comentários.

O campo date/publishDate é 2026-10-20T13:10:00Z, exigido pelo payload; é metadado de rascunho, NÃO agendamento. A leitura posterior com postsListTool confirmou os dois IDs, DRAFT, canais, legendas e ausência de erro. As duas prévias foram relidas pela origem local e referenciam suas respectivas imagens. As imagens servidas localmente foram comparadas byte a byte com os PNGs desta pasta, com igualdade confirmada. Não representa nova auditoria de acesso público externo às prévias.

## Limites e próxima decisão

Aguardando avaliação de arte e legendas pelo titular. Publicação ou agendamento somente com autorização específica do conteúdo, canais e, se aplicável, horário. Alterações após aprovação precisam de nova apresentação antes de publicar.

Nenhum post anterior, canal de outra marca, anúncio, configuração Meta, serviço, credencial ou instalação Hermes foi alterado. Somente estes cinco arquivos finais pertencem ao arquivamento desta produção.
