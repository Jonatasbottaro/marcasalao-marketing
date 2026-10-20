# Marca Salão — Atendimento começa com escuta

Data editorial: 20/10/2026. Fuso: America/Sao_Paulo.
Estado atual: PUBLICADO (PUBLISHED) no Facebook e Instagram em 20/10/2026, após nova autorização humana explícita. IDs originais preservados; artes e legendas sem alterações. A preparação inicial abaixo foi realizada em rascunho.

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

## Histórico da preparação em rascunho — Postiz

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

Na preparação, o campo obrigatório date/publishDate era 2026-10-20T12:00:00Z (09:00 em America/Sao_Paulo). Era metadado do rascunho, não agendamento: naquele momento o estado persistido era DRAFT, sem releaseURL ou releaseId. Na publicação autorizada abaixo, somente o horário e o estado dos registros existentes foram atualizados.

## SHA-256

- legenda-facebook.txt: d0667242a7b6ce3f9ecdc0b2319a13a4c2507ef518d0c65673eacebd232f70c3
- legenda-instagram.txt: 7701920d8f6bf63a7e84aa4830e651d641e3de2e040fc3a1e931739aeb0fc58b
- arte-facebook.png: 2d0cefea4aceb613cd291b01b27a6ae1097a2dc2d0c3833974ef07682c9b1f0e
- arte-instagram.png: 1b2a307a1d7a621d9553fd741dff3644f99add97a407c37013cbd7863f0f0df9

## Limitações e pendências

- Aprovação editorial concluída pelo titular em nova autorização explícita de 20/10/2026, restrita à publicação imediata destes dois IDs. Não autoriza outros posts ou anúncios.
- O acesso HTTP público automatizado ao preview retornou 403. A verificação de anexos foi concluída por leitura na origem local existente, sem alterar proteção, configuração ou credenciais.
- Somente os materiais públicos finais desta pasta devem entrar no Git. Evidências locais e relatório operacional integral ficam fora do repositório. O hash do commit e a confirmação remota constam no relatório operacional, evitando autorreferência no README.
- Sem alterações na Multitrack Hub, no Servidor01, em anúncios, serviços, instalações, permissões ou configurações. Nenhum backup executado para esta tarefa.

## Publicação autorizada — 20/10/2026

O titular revisou artes e legendas e autorizou publicar agora somente os dois rascunhos originais desta pasta. Antes da ação, integrationList e leitura dos dois registros confirmaram canais, DRAFT, legendas e anexos. As artes servidas pela origem local foram novamente comparadas aos arquivos por SHA-256.

Foi utilizado o caminho para registros existentes: PUT /api/posts/<id>/date com action: update e republish: false, definindo o horário corrente sem sair de DRAFT; em seguida, CLI posts:status <id> --status schedule, uma vez por ID, para colocar o registro original na fila de execução imediata. O nome técnico schedule do CLI indica entrada na fila; o horário foi o corrente, não uma publicação futura. Nenhuma chamada de criação, exclusão ou substituição de post foi feita.

Facebook:
- Postiz original: cmvgjipzz0000msbehyin05fs
- Canal: cmvbegwql0001msbhvdpjy0in
- Estado final relido: PUBLISHED; error: null.
- releaseId: 1458106947377490_122110674555500502
- releaseURL: https://www.facebook.com/122109965385500502/posts/122110674555500502
- publishDate: 2026-10-20T10:52:29.181Z (07:52:29 em America/Sao_Paulo; horário de envio à fila, não medição independente do instante de publicação na rede).

Instagram:
- Postiz original: cmvgjiq190001msbex4bcby0w
- Canal: cmvbeq3100003msbhihu2dm4z
- Estado final relido: PUBLISHED; error: null.
- releaseId: 17950030221336735
- releaseURL: https://www.instagram.com/p/DetqZWEIC3t/
- publishDate: 2026-10-20T10:52:29.405Z (07:52:29 em America/Sao_Paulo; horário de envio à fila).

Acompanhamento por leitura CLI passou de QUEUE para PUBLISHED nas duas redes, com releaseURL e releaseId retornados pelo Postiz. Nova leitura individual autenticada dos mesmos IDs confirmou estado, canal, anexo original e texto correspondente às legendas revisadas. Sem reenvio ou duplicação. As legendas foram comparadas normalizando apenas HTML/espaços; arquivos de artes e legendas permanecem byte a byte iguais aos da preparação.

Somente este README foi alterado no repositório nesta etapa. Não foram alterados outros rascunhos, anúncios, a outra marca, serviços ou configurações. A verificação comprova o resultado informado pelo Postiz e seus identificadores de publicação; não inclui nova auditoria visual das páginas públicas nas redes nem do link da bio.
