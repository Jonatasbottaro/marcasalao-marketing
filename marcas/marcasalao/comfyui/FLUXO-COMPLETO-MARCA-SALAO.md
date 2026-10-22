# Marca Salão — fluxo completo sob demanda até rascunho

Autorização do titular em22/10/2026 para o Hermes do Servidor02 e bot @MsalaohermesBot: escolher temas ainda não postados, gerar uma arte no padrão aprovado e as legendas de cada rede e criar rascunhos no Postiz, SEM publicar. Esta é a orientação vigente para pedidos de conteúdo novo desta marca.

## Acionamento e limites

Quando o titular pedir “prepare o próximo conteúdo do MarcaSalão”, “crie conteúdo novo”, “faça o processo completo” ou “crie rascunhos novos”, executar o fluxo inteiro abaixo sem nova confirmação intermediária. Uma solicitação sem quantidade significa UMA campanha: UMA imagem compartilhada e DOIS rascunhos, Facebook/Instagram. Se informar tema, ainda conferir histórico; se já usado, explicar e escolher outro quando o pedido permitir. Se pedir somente ideias/prévia, entregar só essa etapa, sem upload/rascunhos. Esta configuração não gera um post por si só.

Sob demanda: não criar cron, recorrência, rotina diária, monitor ou posts espontâneos. Não publicar nem agendar neste fluxo, inclusive para testar. Aprovação para rascunho não é aprovação de publicação. Uma ordem futura de publicar requer autorização específica dos conteúdos/IDs e canais em procedimento separado. Trabalhar somente no perfil /home/swn/.hermes e canais Marca Salão; não alterar Multitrack, anúncios, serviços, permissões ou credenciais.

## 1. Histórico e escolha do tema

Ler /home/swn/.hermes/POSTIZ-OPERACAO.md, /home/swn/.hermes/COMFYUI-MARCA-SALAO.md e regras do checkout /home/swn/.hermes/workspaces/marketing-marcasalao. Confirmar canais atuais com integrationList: Facebook cmvbegwql0001msbhvdpjy0in e Instagram cmvbeq3100003msbhihu2dm4z.

Consultar postsListTool em janela que cubra TODO o histórico disponível, não apenas o dia atual. Percorrer páginas/janelas adicionais quando houver limite. Filtrar só os dois canais. Cruzar com marcas/marcasalao/posts/*/README.md e legendas. Montar lista de assuntos/ângulos de PUBLISHED, mais temas reservados em DRAFT/SCHEDULED/preparados locais. PUBLISHED evita repetição editorial; DRAFT/preparados evitam duplicação da fila. Não tratar mudança de título/cor como tema novo. Se histórico indisponível/incompleto, não gastar a API alegando ineditismo nem criar duplicatas: informar a pendência.

Escolher um tema ausente das duas listas e registrar no README um motivo curto, fontes e data da consulta. Sem tema fornecido, considerar até três candidatos e escolher um; não gerar três imagens. Conferir alegações de produto em fontes primárias atuais/site/código/documentação validada. Não inventar recursos, preços, métricas, depoimentos ou promessas de resultados. Se não houver fonte de uma funcionalidade, escolher conteúdo editorial útil sem atribuí-la ao sistema.

## 2. Brief, imagem e legendas

Padrão quadrado-compartilhado-ia-v4 em /dados/aplicacoes/comfyui-servidor02/HERMES-POSTIZ.md. Referências aprovadas: anúncio financeiro e “Seu atendimento não termina na cadeira”, arquivados em marcas/marcasalao/posts/2026-10-22-financeiro-quadrado-v4-aprovado e2026-10-22-cuidados-apos-atendimento-previa. Verde-petróleo/menta, logo MS com tesoura, título grande, até três benefícios, salão/mármore/planta/dourado e objetos ligados ao NOVO tema. CTA neutra “Conheça o Marca Salão”, marcasalao.com.br. Não copiar calculadora/finanças para outros temas nem desenhar botões clicáveis.

Preencher um brief JSON com os campos do exemplo-brief.json: campanha slug nova e única para esse tema, tema, titulo, texto (até três benefícios separados por |), direcao_visual, legenda_facebook, legenda_instagram e link_bio_confirmado. Legendas: abertura, contexto/benefícios concretos, orientação útil, pergunta e hashtags. Facebook com URL completa; Instagram link na bio só quando confirmado, caso contrário @marcasalao sem promessa de link. Não editar segredos nem inserir chaves no brief.

Conferir nós MarcaSalaoBriefQuadradoIA, MarcaSalaoArteIA e MarcaSalaoPacoteQuadradoIA via object_info. Executar UMA vez o exportador instalado (default workflow08):

    python3 /dados/aplicacoes/comfyui-servidor02/marcasalao_export.py --brief /caminho/brief.json --state /caminho/estado-exclusivo.json --output /caminho/pacotes

Primeira campanha: até UMA chamada de imagem Gemini2K 1:1, saída1080×1080. Não gerar arte por rede, vertical ou Stories sem pedido. Legendas adaptadas não exigem outra geração de imagem. Não usar workflow06, --artworks ou --background por padrão. Se a arte correta já existe, usar pacote pronto/workflow09 --square-art; não gerar novamente. Timeout: consultar mesmo prompt_id com --resume, fila/histórico e cache antes de qualquer repetição. Não mudar campanha/apagar estado/aumentar revisao para contornar incerteza. Não fazer nova chamada paga automaticamente para corrigir qualidade.

Conferir manifesto/hash, UM PNG e DUAS legendas, media_by_network com ambas as redes apontando ao mesmo arquivo. Abrir/inspecionar a imagem: ortografia/acentos, logo, título/benefícios atuais, CTA/endereço, contraste, ícones, objetos e recortes. Se defeituosa, preservar e informar; não criar rascunho com defeito evidente nem cobrar regeneração sem pedido. Não redesenhar textos/logo localmente. O rascunho será revisão editorial do titular, não aprovação automática de publicação.

## 3. Criar e conferir os dois rascunhos

Consultar integrationSchema atual por rede e consultar novamente posts/mídia antes de criar para evitar corrida/duplicação. Se arte/legenda equivalente já existir, reutilizar IDs em vez de duplicar. Preservar todos os posts/rascunhos anteriores.

Usar CLI oficial /home/swn/.local/bin/postiz upload <PNG> no ambiente privado existente; UM upload e reutilizar mesmo id/path HTTPS nos dois canais quando suportado. Nunca pedir chave/OAuth, substituir imagem por antiga ou usar manifesto como payload. Depois de timeout, consultar biblioteca/posts antes de repetir.

Criar um rascunho por rede via integrationSchedulePostTool, SEMPRE type=draft; usar a legenda integral correspondente. Data exigida pelo schema não muda o tipo para schedule. Não executar comandos now/schedule/publicação.

Reconsultar os registros: IDs/canais corretos, state=DRAFT, releaseURL=null, releaseId=null, legendas exatas (somente newline final pode diferir), mesma mídia persistida nos dois e hash igual à imagem local. Reconfirmar que conteúdos anteriores não mudaram. Se verificação parcial, relatar pendência e IDs existentes; não repetir às cegas.

## 4. Arquivar e entregar

Arquivar localmente em pasta nova marcas/marcasalao/posts/AAAA-MM-DD-tema/: arte-compartilhada-quadrado.png, legenda-facebook.txt, legenda-instagram.txt e README com tema/ineditismo consultado, fontes, SHA, IDs/canais, estado DRAFT e links de prévia, autorização e pendências. Manter estado/cache de geração fora de arquivos públicos. Não sobrescrever legendas originais publicadas. Não fazer push Git automaticamente por este fluxo; publicação do repositório é separada.

No bot, enviar a arte como mídia usando o mecanismo suportado (arquivo local autorizado) e mostrar as duas legendas completas; se corpo comum, mostrá-lo integral e separar CTAs de Facebook/Instagram e encerramento. Se envio inline não estiver disponível, oferecer link de prévia real, sem inventar entrega. Entregar links dos dois rascunhos e informar “rascunhos, nada publicado ou agendado”. Não enviar mensagens a outros destinatários nem outros chats.

Exemplo de pedido do titular: “Prepare o próximo conteúdo inédito do MarcaSalão e deixe os dois rascunhos no Postiz, sem publicar.”
