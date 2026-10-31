# Arquivamento das campanhas de marketing

## Orientação aprovada

O titular autorizou manter no repositório de marketing os materiais finais das campanhas aprovadas e atualizar o registro quando forem publicadas. Esta autorização de arquivamento no GitHub é separada da autorização de publicar ou agendar nas redes sociais.

## Estrutura por marca

- Marca Salão: `marcas/marcasalao/posts/AAAA-MM-DD-tema/`.
- Multitrack Hub: `marcas/multitrackhub/posts/AAAA-MM-DD-tema/`.

Cada perfil trabalha no seu checkout e na sua pasta. O repositório é compartilhado; isso não permite misturar identidades, canais, credenciais ou aprovações.

## O que salvar

1. Arte final aprovada, sem substituir ou alterar silenciosamente a versão apresentada.
2. `legenda-facebook.txt` e `legenda-instagram.txt`, integrais e correspondentes às versões efetivamente aprovadas/publicadas.
3. `README.md` com tema, data editorial, autorização, canais e IDs, estado real verificado, links de prévia/publicação, referências pertinentes e SHA-256 da arte.
4. Roteiro, texto de narração e SRT quando houver vídeo; documentar origem dos arquivos e comandos necessários para reproduzir a edição.
5. Arquivos de vídeo grandes ou ignorados pelo Git precisam de distribuição própria, como assets de uma Release autorizada. Não afirmar que o vídeo está no GitHub só porque seu README foi enviado; validar o arquivo e o link exatos. Ao usar Release, conferir tamanho, download e hash do asset.

## Quando arquivar

- Preparação ainda não aprovada: manter materiais localmente para avaliação; não presumir publicação nas redes.
- Após aprovação da arte e legendas: revisar os arquivos, fazer commit e push da pasta da campanha e conferir o conteúdo remoto.
- Após publicação/agendamento especificamente autorizado: atualizar o README com o estado realmente lido no Postiz e links quando disponíveis, fazer novo commit/push e verificar o remoto.
- Se houver revisão de texto/arte após aprovação, apresentar a versão alterada antes de publicar; manter histórico pertinente sem sobrescrever evidências de conteúdo já publicado.

## Segurança e verificação

- Não incluir `.env`, senhas, tokens, cookies, credenciais, logs de execução, recibos privados, dumps de sessões ou dados de clientes.
- Não registrar conversas privadas inteiras. Resumir somente a autorização necessária, sem dados pessoais desnecessários.
- Selecionar explicitamente arquivos da própria campanha; não usar `git add .` indiscriminadamente.
- Preservar alterações locais de terceiros; não executar reset/clean/stash automático. Conferir remoto e integrar alterações sem force push.
- Serializar pushes dos dois perfis. Se a outra marca avançar a branch, integrar preservando ambos os trabalhos.
- Verificar commit e bytes dos arquivos no remoto antes de dizer que o acervo foi sincronizado. Um commit local não é um push; um push de documentação não envia arquivos ignorados.
- Registrar falhas de sincronização como pendência. Não compensar falha de Git criando, republicando ou excluindo posts nas redes.

## Continuar em outro computador

Clone ou atualize o repositório e abra a pasta da campanha da marca desejada. O README indica o estado conhecido e a fonte da última verificação. Antes de alterar um post, releia o estado atual no Postiz: o arquivo do repositório é histórico documental, não substitui a consulta ao serviço.

Configurações privadas, credenciais e históricos internos do Hermes continuam fora deste repositório. Não é necessário copiar todo o perfil Hermes para consultar as artes e legendas arquivadas.
