# Multitrack Hub — limpeza dos rascunhos de origem após publicação

Regra autorizada pelo titular em 23/10/2026, exclusiva do perfil multitrackhub-marketing no Servidor02. Complementa POSTIZ-OPERACAO.md e o skill Postiz existente. Não é uma rotina recorrente, não autoriza publicar/agendar, nem uma varredura dos rascunhos antigos.

## Quando executar

Somente ao concluir uma publicação específica autorizada pelo titular nos DOIS canais: Facebook cmvbss5fn0005msbhhbdy6ing e Instagram cmvbsudg50007msbh2j4734i4. Pedido de criar rascunhos ou prévia termina em DRAFT, sem limpeza. Uma chamada aceita, QUEUE, processamento, timeout ou confirmação de apenas uma rede não autoriza remover nenhum dos rascunhos de origem.

## Vínculo obrigatório da campanha

Ao criar os dois rascunhos, persistir na pasta da campanha um registro postiz-operacao.json próprio, separado do manifest.json de arte. Campos mínimos: brand=multitrackhub, campaign, media_url e image_sha256, captions por rede (texto ou hash), source_drafts com os dois IDs e integrationIds, publications por rede com IDs retornados, status e releaseURL/releaseId; cleanup com candidatos, estado, verificações e resultado por ID. Atualizar esse registro em cada etapa. Jamais escrever chave/token.

Registrar os IDs dos rascunhos ANTES de publicar. Uma ferramenta de publicação pode criar IDs novos em vez de converter os rascunhos; não prometer que serão os mesmos IDs. Se a publicação converter o próprio rascunho para PUBLISHED, preservar esse ID e registrar que não restou rascunho para remover. Se criar IDs novos, conservar o vínculo explícito rascunho → publicação por rede. Não inferir origem por título, horário, ordem no calendário, hash ou URL de imagem isolados. Sem vínculo comprovado, não apagar nada e relatar pendência. Campanhas antigas sem registro não são candidatas automáticas.

## Confirmação obrigatória nas duas redes

Consultar estado atual de ambos os IDs de publicação em Postiz. Exigir PUBLISHED, error vazio e URL pública final releaseURL não vazia para CADA rede. Confirmar que IDs e integrationIds pertencem à campanha e somente aos dois canais permitidos. Se postsListTool não trouxer releaseURL, consultar a leitura disponível da API pública local /public/v1/posts ou prévia que comprove o destino; não enfraquecer a regra para aceitar apenas o retorno da criação. Nunca exibir credencial. Conferir a mídia salva e a legenda de cada rede contra as aprovadas (normalizar apenas HTML, entidades e espaços). Não comparar a legenda Facebook com a Instagram como se fossem iguais.

Antes de qualquer DELETE, formar a lista completa de candidatos e validar TODOS; se algum candidato for ambíguo ou diferente, abortar a limpeza inteira. Exigir para cada candidato:
- ID exato em source_drafts desta campanha, no canal correto, diferente dos IDs publicados;
- estado atual DRAFT, releaseURL/releaseId vazios e sem agendamento (publishDate técnico em DRAFT não é agendamento);
- mesma mídia e legenda daquela rede registradas antes da publicação, sem edições posteriores;
- ausência de outras entradas/threads de postagem não pertencentes à campanha que a remoção pudesse atingir. Se o alcance da remoção não estiver claro, não remover.

## Remoção e verificação

O titular autorizou esta limpeza vinculada após publicação confirmada nas duas redes; não pedir confirmação intermediária quando todas as condições acima estiverem satisfeitas. Usar CLI oficial, um ID por vez:

    /home/swn/.local/bin/postiz posts:delete ID_EXATO_DO_RASCUNHO

Nunca passar ID de publicação; não usar comandos em lote ou seleção de todos. Preservar biblioteca de mídia, PNGs, legendas, manifestos, histórico e outros rascunhos, inclusive campanhas semelhantes. Não tocar canais/publicações/rascunhos MarcaSalão.

Após cada remoção, reconsultar Postiz: confirmar ausência somente do candidato removido e permanência das duas publicações. Ao final, comparar com inventário anterior à limpeza e conferir que os demais registros permanecem iguais. Se erro/timeout ocorrer, reconsultar antes de repetir; ID já ausente é removido, não é motivo para recriar ou publicar de novo. Uma limpeza parcial não deve ser relatada como completa. Falha da segunda remoção não autoriza restaurar, modificar ou republicar as publicações.

Salvar no postiz-operacao.json o inventário/evidência suficiente para auditoria, IDs removidos, preservados, horários no fuso America/Sao_Paulo e resultado. Responder com links das publicações e resumo da limpeza; não chamar os links publicados de rascunhos. Reexecução com os candidatos já ausentes deve terminar como já concluída, sem novos writes. Este ajuste de regra, por si só, não executa DELETE em nenhum registro atual.
