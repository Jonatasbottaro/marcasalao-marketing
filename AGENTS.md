# Regras do projeto Marca Salão Marketing

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

Consulte `WORKFLOW.md` para o fluxo completo.

## Chamadas para o site Marca Salão — padrão de 19/10/2026
- Destino oficial: https://marcasalao.com.br.
- Facebook: usar URL completa na legenda e indicação “Acesse pelo link da descrição”.
- Instagram: orientar “Conheça o sistema — link na bio”; conferir link do perfil antes de prometer esse acesso. URL em imagem não é botão e link em legenda não deve ser presumido clicável.
- Nas próximas artes de feed Marca Salão, usar chamada específica por rede: “Acesse o link da descrição” no Facebook; “Acesse o link na bio” no Instagram. Evitar aparência de botão clicável embutido em imagem estática.
- Stories com adesivo de link são outro formato e requerem pedido/autorização para publicação; não inferir que um botão desenhado faça isso.
- Não republicar para corrigir legenda; editar somente o post existente e validar. Não prometer que edição no Postiz sincroniza texto de post já publicado nas redes.
- Preservar legenda.txt como versão original publicada; revisões por rede em legenda-facebook.txt e legenda-instagram.txt, com data/estado real no registro.
- Este ajuste não altera anúncios ou os posts da Multitrack Hub.

## Chamadas para o site Multitrack Hub — 19/10/2026
- Site oficial https://multitrackhub.com.br; para rateios https://multitrackhub.com.br/rateios.
- Facebook: URL completa na legenda, com Acesse pelo link da descrição.
- Instagram: Link na bio do @multitrackhub; tema rateios orienta abrir a seção Rateios pelo site. Conferir link externo real cadastrado; texto em biografia não basta.
- Próximas artes: chamada específica por rede, sem simular botão clicável na imagem. Stories com adesivo são outro formato e precisam de autorização para publicar.
- Preservar posts e legenda.txt originais; manter revisões em legenda-facebook.txt e legenda-instagram.txt. Edição nativa não comprova sincronização do histórico Postiz.
- Não configurar WhatsApp/telefone comercial nem alterar Marca Salão ou anúncios.

## Arte quadrada compartilhada Marca Salão — 22/10/2026

Por pedido posterior explícito do titular: gerar somente UMA arte quadrada e usar o mesmo arquivo nas duas redes, com legendas adaptadas para economizar API. Neste modo, usar CTA neutra “Conheça o Marca Salão” na imagem; substitui a chamada específica por rede dentro da arte. Manter URL completa na legenda Facebook e link da bio no Instagram somente confirmado. Outros formatos/segunda arte só mediante pedido. Workflow08 é padrão; workflow09/--square-art reutiliza uma arte sem Gemini. Não publicar/agendar nem criar rascunhos por um pedido de configurar/prévia.

## Conteúdo novo pelo bot Marca Salão — autorização22/10/2026

O titular autorizou o fluxo sob demanda até DRAFT: consultar temas publicados e reservados, escolher UM tema ainda não usado, gerar UMA arte quadrada no padrão aprovado e duas legendas, revisar, enviar uma mídia compartilhada e criar/conferir DOIS rascunhos Postiz. Leia /home/swn/.hermes/FLUXO-COMPLETO-MARCA-SALAO.md. Pedidos de conteúdo novo/processo completo acionam esse fluxo sem confirmação intermediária; pedidos apenas de ideias/prévia continuam limitados ao solicitado. Uma campanha e até uma chamada de imagem por pedido sem quantidade; não regenerar automaticamente em erro/qualidade ruim. Não criar recorrência, publicar/agendar, tocar outras marcas/conteúdos anteriores nem fazer push automático. Este pedido de configuração não gera nova campanha por si só.

## Proveniência obrigatória e revisões —23/10/2026

A nova arte Marca Salão deve ser produzida no ComfyUI08, sem substituição manual. Após gerar, usar /dados/aplicacoes/comfyui-servidor02/marcasalao_media_guard.py upload --package PACOTE --prompt-id UUID --state NOVO.json para validar e registrar a mídia. O hook bloqueia DRAFT com mídia não validada e criações repetidas para o mesmo canal/mídia; o CLI direto Marca Salão também é protegido. Não contornar os bloqueios com outro cliente/caminho interno/HTTP. Revisões atualizam os IDs existentes; não criam outro par. Remover duplicados somente mediante autorização explícita. Preservar os demais posts e manter DRAFT, sem publicar/agendar.
