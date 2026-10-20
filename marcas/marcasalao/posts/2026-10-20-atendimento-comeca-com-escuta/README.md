# Marca Salão — Atendimento começa com escuta

Data editorial: 20/10/2026. Fuso: America/Sao_Paulo.
Estado: dois novos RASCUNHOS (DRAFT), um por rede. Não publicado, não agendado.

## Tema e razão da escolha

Orientação editorial para o atendimento: perguntar o que a pessoa deseja mudar, o que prefere manter e como é sua rotina de cuidados antes de começar o serviço. As perguntas são sugestões editoriais, não um protocolo técnico ou uma promessa de resultado.

Antes da criação, foram consultados integrationList, postsListTool (janela 2020–2030) e os posts existentes no repositório. Os conteúdos anteriores tratam de apresentação, fluxo de agendamento, organização de agenda/equipe e finanças; os rascunhos de 19/10 tratam da escolha de serviço, profissional e horário. O tema escuta e alinhamento de expectativas é diferente e não recria esses materiais. Os registros anteriores não foram editados.

## Fontes e limites

- Site oficial consultado nesta execução: https://marcasalao.com.br. A seção de recursos relaciona preferências dos clientes à personalização do atendimento. Essa referência orienta o tema, mas o post NÃO afirma que as três perguntas sejam campos, automações ou recursos implementados no sistema. Não foi feito teste funcional de CRM.
- Logo oficial: https://marcasalao.com.br/icons/icon-512x512.png, baixada e conferida visualmente: MS serifado com tesoura. Correspondência com a referência aprovada em marcas/marcasalao/posts/2026-10-18-apresentacao-agendamento/marcasalao-apresentacao-agendamento.png.
- Contexto de identidade: docs/hermes/2026-10-18/BOT-MARCA-SALAO.md. Paleta verde-petróleo, menta e branco; logo oficial preservada, sem redesenho. Composição tipográfica nova, sem reaproveitar a arte antiga como post novo, sem telas fictícias ou botão clicável simulado.
- Link externo do Instagram validado no registro docs/hermes/2026-10-19/CORRECAO-LINKS-MARCA-SALAO.md, conclusão de 19/10. Não houve nova auditoria do perfil nesta execução; reconferir antes de eventual publicação.
- Sem preços, estatísticas, prazos, depoimentos, promessas comerciais ou de resultado. Não reproduz alegações quantitativas da landing page.

## Arquivos finais

- arte-facebook.png: PNG RGB, 1080 × 1080, CTA “Acesse o link da descrição”.
- arte-instagram.png: PNG RGB, 1080 × 1080, CTA “Acesse o link na bio”.
- legenda-facebook.txt: endereço completo do site e CTA para descrição.
- legenda-instagram.txt: CTA para bio do @marcasalao.
- README.md: registro sanitizado.

As duas artes foram abertas para revisão visual: texto em português legível, acentuação, margens, logo e CTAs conferidos. Produção com Pillow já instalado, sem instalar ferramentas. Conteúdo estático; SRT, vídeo e áudio não se aplicam.

## Persistência Postiz

Schemas de Facebook, Instagram e da ferramenta de criação consultados. Uma única chamada MCP criou exatamente dois registros, ambos com type: draft, post_type: post e sem comentários. Não houve repetição da criação.

Facebook:
- Canal: cmvbegwql0001msbhvdpjy0in
- Novo post: cmvgjipzz0000msbehyin05fs
- Preview: https://postiz.swnsolucoes.com.br/p/cmvgjipzz0000msbehyin05fs?share=true
- Mídia: a63d2bc9-e318-4f87-99ff-5f5cc841aced
- Path: https://postiz.swnsolucoes.com.br/uploads/2026/10/20/44f8fa99ecf3d8e75a10db1b1049a05884.png

Instagram:
- Canal: cmvbeq3100003msbhihu2dm4z
- Novo post: cmvgjiq190001msbex4bcby0w
- Preview: https://postiz.swnsolucoes.com.br/p/cmvgjiq190001msbex4bcby0w?share=true
- Mídia: 1f8291a9-fc14-404f-ac68-8a691cdc6dab
- Path: https://postiz.swnsolucoes.com.br/uploads/2026/10/20/3766232bf83d5443121c9638c6ad616f.png

Upload CLI retornou ready para ambas, seguido de confirmação por mediaListTool. postsListTool confirmou IDs, canais, textos e DRAFT. Leitura CLI confirmou releaseURL: null e releaseId: null nos dois. Os previews relidos na origem local contêm as respectivas imagens novas em elementos img. Os bytes das mídias servidas pela origem local foram comparados com os PNGs locais por SHA-256: correspondência exata. Legendas salvas comparadas programaticamente ao conteúdo persistido, ignorando apenas marcação HTML e espaços de apresentação.

O campo obrigatório date/publishDate é 2026-10-20T12:00:00Z (09:00 em America/Sao_Paulo). É metadado obrigatório do rascunho, não agendamento: o estado persistido é DRAFT, sem releaseURL ou releaseId.

## SHA-256

- legenda-facebook.txt: d0667242a7b6ce3f9ecdc0b2319a13a4c2507ef518d0c65673eacebd232f70c3
- legenda-instagram.txt: 7701920d8f6bf63a7e84aa4830e651d641e3de2e040fc3a1e931739aeb0fc58b
- arte-facebook.png: 2d0cefea4aceb613cd291b01b27a6ae1097a2dc2d0c3833974ef07682c9b1f0e
- arte-instagram.png: 1b2a307a1d7a621d9553fd741dff3644f99add97a407c37013cbd7863f0f0df9

## Limitações e pendências

- Revisão/aprovação editorial pelo titular antes de qualquer publicação. Este fluxo não autoriza publicar nem agendar.
- O acesso HTTP público automatizado ao preview retornou 403. A verificação de anexos foi concluída por leitura na origem local existente, sem alterar proteção, configuração ou credenciais.
- Somente os materiais públicos finais desta pasta devem entrar no Git. Evidências locais e relatório operacional integral ficam fora do repositório. O hash do commit e a confirmação remota constam no relatório operacional, evitando autorreferência no README.
- Sem alterações na Multitrack Hub, no Servidor01, em anúncios, serviços, instalações, permissões ou configurações. Nenhum backup executado para esta tarefa.
