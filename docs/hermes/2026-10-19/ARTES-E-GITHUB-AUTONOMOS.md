# Artes locais e GitHub — autonomia dos bots no Servidor02

Atualização de 19/10/2026. Complementa [a conexão MCP](POSTIZ-CONFIGURACAO.md) e os [prompts por marca](../README.md). O Hermes do Servidor01/VPS não foi alterado.

## Fluxo instalado
1. Criar arte local e legendas por rede na identidade da marca.
2. Enviar arquivo local com o CLI oficial Postiz, sem navegador: `/home/swn/.local/bin/postiz upload /caminho/absoluto/arte.png`.
3. Confirmar retorno de mídia `id`, `path` HTTPS e `status`; consultar a biblioteca quando necessário. O comando upload só envia mídia, não cria ou publica post.
4. Usar o campo `path` retornado nas attachments do MCP. Consultar integrationSchema e salvar com `integrationSchedulePostTool`, `type: draft`, somente nos IDs permitidos da marca.
5. Conferir rascunho persistido e anexo correto. Não trocar a arte nova por imagem antiga silenciosamente.
6. Copiar arte final, legendas e README sanitizado para a pasta da marca no checkout próprio; commit/push pelo Git SSH já configurado.
7. Confirmar arquivos remotos e informar commit, rascunhos e pendências. Publicação e agendamento continuam dependendo de autorização específica do titular.

## Upload sem depender do navegador
CLI oficial `postiz` versão 2.0.25, instalado no diretório do usuário a partir do pacote npm oficial. A instalação do CLI não atualizou a aplicação Postiz nem o Coolify.

Cada perfil possui `POSTIZ_API_KEY` e `POSTIZ_API_URL` no ambiente privado, com arquivo 0600. O CLI usa a origem do mesmo servidor, `http://127.0.0.1:4007/api`, e acrescenta `/public/v1/upload`. A resposta fornece URL HTTPS pública para a mídia.

Não imprimir variáveis ou arquivos .env, copiar credenciais ao comando ou repositório, executar auth:login, rotacionar chave ou alterar o navegador para fazer um upload local. O MCP existente continua usando Bearer; o CLI trata seu próprio cabeçalho REST. Não misturar payload REST de posts com schema MCP.

Não usar posts:create, posts:status, posts:delete ou publicação como teste de upload. Se o comando falhar, preservar o arquivo e informar o erro sem segredos; não declarar a arte anexada sem confirmação.

## Checkouts separados e autenticados
| Perfil | Checkout de marketing | Pasta editorial permitida |
|---|---|---|
| Marca Salão | `/home/swn/.hermes/workspaces/marketing-marcasalao` | `marcas/marcasalao/` |
| Multitrack Hub | `/home/swn/.hermes/profiles/multitrackhub-marketing/workspaces/marketing-multitrackhub` | `marcas/multitrackhub/` |

Repositório: https://github.com/Jonatasbottaro/marcasalao-marketing. Autenticação SSH com chave já existente do Servidor02, específica desse repositório, configurada no `.git/config` de cada checkout. Nenhuma chave/token ou permissão GitHub nova foi criada. O checkout antigo do usuário foi preservado.

A separação de pastas e perfis é operacional. A chave permite escrita no repositório inteiro; a chave Postiz também abrange a organização compartilhada. Não afirmar isolamento técnico por marca.

Antes de editar, conferir status e preservar trabalho desconhecido. Com árvore limpa, pull --ff-only. Adicionar somente a pasta do conteúdo da marca, conferir diff, commit e push origin main sem force. Se outro bot avançou main, pull --rebase e novo push após conferir; parar diante de conflito que não possa resolver sem perda. Não usar reset/clean para descartar trabalho, nem git add . na raiz.

Não é necessário gh auth login, token HTTPS, conector do Codex ou outro checkout para arquivar. Consulte `GITHUB-MARKETING-OPERACAO.md` na raiz do perfil local. Apenas artes finais, legendas, SRT/texto de narração quando aplicável e README de status/fontes/IDs; nunca acervo inteiro, logs, HTMLs de sessões, .env, chaves ou RESULTADO.md integral sem revisão.

## Validação sem publicação
Os próprios bots locais foram instruídos a enviar as artes já preparadas e arquivá-las no GitHub, sem criar ou alterar posts. Leituras posteriores de mídia e Git/remoto confirmam os resultados registrados na documentação operacional privada. Os quatro posts do teste anterior permanecem DRAFT; os novos uploads de validação são somente biblioteca, preservando anexos existentes.

Conteúdos arquivados como rascunho:
- [Marca Salão — escolha de serviço, profissional e horário](../../../marcas/marcasalao/posts/2026-10-19-escolha-servico-profissional-horario/).
- [Multitrack Hub — prepare seu próximo ensaio](../../../marcas/multitrackhub/posts/2026-10-19-prepare-seu-ensaio/).

A regra de vídeos sem áudio do AGENTS.md, o CTA específico por rede, a ausência de WhatsApp comercial na Multitrack Hub e a preservação dos anúncios continuam em vigor. Não reinstalar configurações de outra máquina.

## Operação e retorno
Um backup completo foi confirmado antes da alteração, com cópias privadas anteriores dos perfis para retorno seletivo. Guias locais POSTIZ-OPERACAO.md, GITHUB-MARKETING-OPERACAO.md e SOUL.md foram atualizados; gateway/dashboard do Servidor02 foram recarregados. O procedimento completo, snapshot, verificações e retorno ficam no documento privado HERMES-ARTES-GITHUB-CORRECAO-2026-10-19.md do acervo oficial.

Para desfazer, preservar mudanças posteriores e restaurar apenas as variáveis/referências acrescentadas e configuração local dos checkouts. Não revogar a chave SSH existente, canais ou app Meta para desfazer esta integração. Não excluir arquivos ou commits de marketing automaticamente.

### Commits de validação dos próprios bots
- Marca Salão: [3baaaaf](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/3baaaaf9bbdf86975542aceb27433afc40876fd4), cinco arquivos.
- Multitrack Hub: [47db4ac](https://github.com/Jonatasbottaro/marcasalao-marketing/commit/47db4acfef23e4c89a6ee4fc9d9782d73f732414), quatro arquivos, preservando o commit da outra marca.
Verificação independente: nove arquivos remotos correspondem aos originais locais; três uploads dos bots confirmados na biblioteca; os 16 registros sociais anteriores permaneceram sem alteração (12 publicados históricos e quatro rascunhos). Nenhuma nova publicação ou alteração de anexos foi usada para validar o acesso.
