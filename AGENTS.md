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
