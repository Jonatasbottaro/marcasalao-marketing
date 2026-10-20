# Hermes e Postiz — configuração validada em 19/10/2026

Este documento substitui as afirmações antigas de que a integração Hermes/Postiz ainda não estava instalada. A conexão foi corrigida e testada nos dois perfis LOCAIS do Servidor02. O Hermes do Servidor01/VPS ficou fora do trabalho.

## Prompts para cada bot

- [Marca Salão](PROMPT-BOT-MARCA-SALAO.md).
- [Multitrack Hub](PROMPT-BOT-MULTITRACK-HUB.md).
- [Histórico completo de marcas, artes e publicações](../2026-10-18/GUIA-COMPLETO.md).

Importar os prompts não autoriza criar ou publicar um post: a primeira ação prevista é conferir os canais por leitura.

## Perfis e IDs Postiz

| Marca | Perfil local do Hermes | Canal Facebook | Canal Instagram |
|---|---|---|---|
| Marca Salão | padrão, `/home/swn/.hermes` | `cmvbegwql0001msbhvdpjy0in` — Meu salão | `cmvbeq3100003msbhihu2dm4z` — @marcasalao |
| Multitrack Hub | `/home/swn/.hermes/profiles/multitrackhub-marketing` | `cmvbss5fn0005msbhhbdy6ing` — Multitrack Hub | `cmvbsudg50007msbh2j4734i4` — @multitrackhub |

São IDs de integração do Postiz. Não substituí-los por IDs de Páginas, contas Instagram ou ativos comerciais da Meta.

Os quatro canais compartilham uma organização Postiz e uma chave. A separação entre bots é operacional, por instruções e seleção de IDs; não é uma barreira de permissões. Não afirmar que cada credencial só permite acessar dois canais.

## Conexão instalada

- Painel público: https://postiz.swnsolucoes.com.br.
- MCP: nome `postiz`, habilitado em ambos os perfis.
- Transporte HTTP na origem do mesmo servidor: `http://127.0.0.1:4007/api/mcp`. Esse endereço não funciona a partir de outra máquina sem uma configuração própria.
- Autenticação MCP: cabeçalho `Authorization: Bearer ${MCP_POSTIZ_API_KEY}`.
- A variável está nos arquivos privados de cada perfil. YAML contém somente a referência à variável; nenhum valor de chave faz parte deste repositório.
- Tempo de conexão: 30 segundos; chamada de ferramenta: 90 segundos.
- Chave existente reutilizada com autorização do titular, sem rotação.
- Outros MCPs, configurações e valores privados preexistentes preservados.
- Gateway e dashboard locais reiniciados após a alteração e confirmados ativos.
- Nenhuma alteração em Postiz/Coolify, credenciais Meta, anúncios ou Hermes do Servidor01 para instalar esta conexão.

A API REST usa a chave diretamente no cabeçalho Authorization; o MCP instalado usa Bearer. Não misturar os dois formatos nem usar o corpo REST de criação de posts numa ferramenta MCP.

## Ferramentas expostas aos bots

1. `integrationList`: listar canais.
2. `integrationSchema`: consultar requisitos do canal antes de preparar postagem.
3. `integrationSchedulePostTool`: criar rascunho, agendar ou publicar conforme autorização.
4. `postsListTool`: consultar posts e evitar duplicações.
5. `postSettingsTool`: ajustar configurações de post quando solicitado.
6. `mediaListTool`: consultar mídia existente.
7. `uploadFromUrlTool`: enviar mídia por URL quando necessário ao conteúdo solicitado.

O servidor oferece 18 ferramentas na descoberta; apenas as sete acima foram habilitadas na configuração. Agente genérico e geração de imagem/vídeo do Postiz ficaram fora desta conexão. Não ativar outras funções automaticamente para contornar uma falha.

## Fluxo editorial obrigatório

1. Identificar a marca e consultar seu contexto, logos e artes aprovadas em `marcas/marcasalao/` ou `marcas/multitrackhub/`.
2. Confirmar recursos e condições no site oficial; não inventar funcionalidades, preços, números, prazos ou regras de rateio.
3. Preparar arte e legendas por rede. Facebook: URL completa clicável na legenda. Instagram: chamada para o link da bio. Imagem estática não possui botão clicável.
4. Confirmar com `integrationList` os dois IDs permitidos e consultar `integrationSchema`.
5. Criar somente rascunho: `integrationSchedulePostTool` com `type: draft`. Seguir o schema atual da ferramenta, inclusive data UTC e configurações de cada rede; não inferir agendamento a partir da data de um rascunho.
6. Arquivar arte, `legenda-facebook.txt`, `legenda-instagram.txt` e README de status/fontes/IDs em `marcas/<marca>/posts/AAAA-MM-DD-<tema>/`. Preservar `legenda.txt` e versões já publicadas.
7. Mostrar prévia, canais, IDs e status real. Rascunho não é publicação. Falha de salvamento não pode ser relatada como sucesso.
8. Usar `type: now` ou `type: schedule` somente após autorização explícita daquele conteúdo, destinos e horário. Aprovações antigas não abrangem novos conteúdos; mudanças posteriores exigem nova revisão.
9. Após autorização e execução, conferir status e postagem real em cada rede. Se houver falha parcial ou timeout, consultar antes de repetir para não duplicar.

Para vídeos, seguir o AGENTS.md: sem áudio, legendas visíveis, SRT e texto de narração separado. Não gerar áudio. Não alterar anúncios ou permissões. Multitrack Hub continua sem WhatsApp e sem telefone comercial.

## Verificações realizadas

- GET autenticado da API de integrações: HTTP 200, quatro canais ativos.
- Handshake MCP e descoberta das 18 ferramentas.
- Chamada autenticada de `integrationList` em cada perfil: sucesso e quatro canais com IDs conferidos.
- `hermes mcp test postiz` nos dois perfis: Connected, exit 0.
- Sete ferramentas escolhidas disponíveis no servidor.
- Comparação da configuração restante e do conteúdo privado preexistente: preservados.

Nenhuma chamada de escrita, criação de rascunho, agendamento ou publicação foi executada para testar. A autenticação e as leituras foram verificadas; uma nova publicação depende de autorização e das condições atuais do canal.

## Uso e diagnóstico

Em cada bot, pedir:

> Use o Postiz para listar somente os canais da sua marca, sem criar ou publicar nada.

Conversa antiga pode manter ferramentas em cache. Executar `/reload-mcp` e confirmar a recarga solicitada pelo Hermes, ou abrir nova conversa. Não desativar permanentemente a confirmação de recarga para resolver esse caso.

O erro anterior era `OAuthRegistrationError: Invalid registration response`, com redirecionamento para uma página de login. A entrada OAuth foi substituída pela conexão por cabeçalho. Não executar `hermes mcp login postiz`, rotacionar chave, revogar o app Meta ou recriar canais para esse problema.

Se a origem local não responder, conferir o serviço Postiz e seu mapeamento local. Se responder 401, conferir a presença da variável privada no perfil correto sem imprimir seu valor. Não usar outro perfil ou credencial de VPS por semelhança de nome.

Não contornar bloqueio da borda pública, imitar outro cliente, mudar Cloudflare ou expor a porta local como tentativa automática de correção.

## Documentação privada e retorno

Cada perfil contém `POSTIZ-OPERACAO.md` e uma orientação no `SOUL.md` com seus canais. Diagnóstico, backup concluído antes da mudança, cópias anteriores e retorno seletivo estão no acervo oficial do Servidor02, em `HERMES-POSTIZ-DIAGNOSTICO-2026-10-19.md`.

Para desfazer, restaurar somente a entrada Postiz anterior e a variável acrescentada de cada perfil, preservando mudanças posteriores; recarregar os serviços locais. Não restaurar toda a configuração por cima de alterações do usuário. A reversão não exige mudar Meta ou anúncios.

Não publicar arquivos .env, chaves, cookies, tokens, configurações exportadas, snapshots privados ou a conversa bruta.


## Complemento — upload local e GitHub autônomos
O CLI oficial Postiz 2.0.25 foi instalado para envio direto de arquivos locais, com ambiente privado por perfil, e os dois bots receberam checkouts SSH separados com escrita no repositório de marketing. Isso resolve a dependência do navegador para upload e a falta de autenticação de escrita que apareceram no primeiro teste. Não depende do conector GitHub do Codex nem de novo OAuth. Ver [procedimento e limites](ARTES-E-GITHUB-AUTONOMOS.md). Preparação continua rascunho; nenhuma autorização genérica de publicação foi concedida.
