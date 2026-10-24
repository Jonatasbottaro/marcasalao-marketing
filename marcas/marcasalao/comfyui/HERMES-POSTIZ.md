# Marca Salão — uma arte quadrada compartilhada — padrão v4

## Padrão vigente aprovado em 22/10/2026

Gerar UMA imagem quadrada por campanha e reutilizar o mesmo arquivo em Facebook e Instagram. Criar duas legendas adaptadas. Nenhum formato vertical/Stories nem segunda arte por rede por padrão. O objetivo explícito é economizar API. Padrão visual realista da referência https://www.facebook.com/photo/?fbid=122109973515500502 e prompt reverso em custom_nodes/servidor02_gemini/assets/padrao-arte-integral.txt continuam: Gemini cria a arte completa, com logo/textos/ícones; só escalar localmente, nunca redesenhar nem recortar. Sem modelos locais.

A arte compartilhada usa CTA neutra “Conheça o Marca Salão” e marcasalao.com.br, sem simular botão clicável. Esta decisão posterior substitui as chamadas específicas por rede dentro da imagem neste modo. As chamadas específicas permanecem nas legendas. Não compartilhar uma arte antiga que prometa link da descrição/bio incorreto para a outra rede; usar arte de CTA neutra ou pedir revisão.

## Workflow econômico padrão

Conferir /object_info/MarcaSalaoBriefQuadradoIA, /object_info/MarcaSalaoArteIA e /object_info/MarcaSalaoPacoteQuadradoIA antes de executar. Se ausentes, não usar silenciosamente o fluxo de seis gerações.

- 08-marcasalao-quadrado-compartilhado: brief → UM MarcaSalaoArteIA com rede=compartilhado, formato=quadrado, revisao=1 → MarcaSalaoPacoteQuadradoIA.
- Uma execução inédita gera somente uma chamada Gemini de imagem 2K em 1:1; saída final RGB 1080×1080. Até uma chamada por arte/revisão, sem repetição automática.
- Cache completo com SHA válido reutiliza a arte sem nova chamada. Original, prompt e metadados em /data/output/marcasalao/geracoes-ia/<campanha>/<assinatura>/. Estado incompleto/incerto bloqueia repetição: inspecionar antes de refazer. Só aumentar revisao quando uma nova geração for de fato necessária/autorizada.
- 09-marcasalao-reutilizar-quadrado: um LoadImage com arte completa existente → pacote. Nenhuma chamada Gemini. Não passar arte pronta ao --background.
- Workflows 06/07 de seis variantes e 04/05 de composição local são históricos/opcionais; nunca padrão. Só usar formatos extras quando o titular pedir explicitamente.

## Exportador

    python3 /dados/aplicacoes/comfyui-servidor02/marcasalao_export.py --brief /caminho/brief.json --state /caminho/estado-novo.json --output /caminho/pacotes

Esse comando agora usa workflow08. Para uma arte quadrada neutra já existente, acrescentar --square-art /caminho/arte.png (workflow09, zero Gemini). --resume /caminho/estado.json consulta o MESMO prompt_id, sem reenviar. Estado deve ser novo e é reservado antes do envio. Timeout exige consultar fila/histórico e cache; não apagar estado nem mudar campanha para contornar a proteção. Histórico pode desaparecer após reinício, mas arquivos/cache persistem: reutilizar pacote pronto ou workflow09. Chave permanece no ambiente privado do Coolify; nunca copiar para documentos.

--artworks com seis arquivos continua disponível apenas para recuperação de pacotes antigos; --background é legado de composição local. Não usar essas opções por padrão.

## Contrato de pacote e integração

manifest.json schema_version=1, visual_standard=quadrado-compartilhado-ia-v4, status=prepared, review_required=true, publication_authorized=false. Há UM PNG arte-compartilhada-quadrado.png, images com uma entrada network=compartilhado e format=quadrado, e duas legendas legenda-facebook.txt/legenda-instagram.txt. postiz.media_by_network mapeia ambas as redes para o mesmo arquivo. postiz.preferred_feed_format=quadrado, mode=draft_only, media_uploaded=false e drafts_created=false. Não exigir seis imagens no modo v4. Verificar hashes e dimensões antes de integrar. Não é payload de criação Postiz.

## Brief e legendas

Preencher exemplo-brief.json com fatos verificáveis, campanha slug, tema/titulo atuais, até três benefícios separados por | ou quebra de linha e direcao_visual pertinente. Nunca copiar os benefícios financeiros para temas diferentes.

Hermes escreve corpo das duas legendas: abertura, benefício/contexto, até três recursos com explicação concreta, orientação útil, pergunta final e três a cinco hashtags. O exportador preserva o corpo e insere CTA antes de pergunta/hashtags. Facebook recebe URL completa https://marcasalao.com.br e indicação do link da descrição. Instagram recebe “Conheça o sistema — link na bio” somente se o link externo real estiver confirmado; caso contrário “Conheça o Marca Salão: @marcasalao”. Confirmação registrada em 19/10 deve ser reavaliada se o perfil mudar. Essa adaptação textual não chama uma API de imagem.

## Revisão e Postiz

Conferir nome/logo/tesoura, ortografia/acentos, título e benefícios, CTA neutra, contraste e cenário. Sucesso da API não comprova qualidade. Apresentar uma arte e as duas legendas integrais para avaliação. Nenhum workflow/exportador acessa Postiz. Pedido de configurar/prévia não autoriza uploads, rascunhos, agendamento nem publicação.

Quando o titular pedir rascunhos, consultar POSTIZ-OPERACAO.md, integrationList, posts existentes e schemas atuais antes de criar, evitando duplicação. Somente canais Marca Salão: Facebook cmvbegwql0001msbhvdpjy0in e Instagram cmvbeq3100003msbhihu2dm4z. Usar a MESMA imagem e a legenda correspondente; reutilizar URL de mídia válida se suportada, evitando uploads desnecessários. Caminhos locais não são URLs Postiz. Criar type=draft, reconsultar DRAFT e releaseURL/releaseId nulos. Preservar posts/rascunhos anteriores. Publicar/agendar exige autorização específica; não alterar Multitrack Hub.

## Acionamento completo pelo bot — autorização posterior22/10/2026

Leia /home/swn/.hermes/FLUXO-COMPLETO-MARCA-SALAO.md para pedidos de conteúdo novo/processo completo. O titular autorizou o bot Marca Salão a escolher tema inédito, gerar uma arte e duas legendas e criar os dois rascunhos DRAFT sob demanda, sem confirmação entre as etapas. Isso não autoriza publicar/agendar nem criar recorrência. Pedido somente de prévia permanece sem upload/rascunho. Conferir também temas já reservados em rascunhos/preparados locais. Uma campanha por pedido, uma chamada de imagem; falha/qualidade ruim não autoriza regeneração automática. Apresentar arte e legendas completas após conferir os DRAFT. Esta orientação complementa o fluxo v4 sem mudar ComfyUI, credenciais ou Postiz.

## Envio obrigatório com validação — correção23/10/2026

Nova arte de campanha precisa do workflow08 e de pacote correspondente à saída real do ComfyUI. É proibido substituir por composição manual local. Se o ComfyUI não estiver disponível, parar e informar, sem fallback visual. Antes do upload, executar:

    python3 /dados/aplicacoes/comfyui-servidor02/marcasalao_media_guard.py upload --package /caminho/pacote --prompt-id UUID_COMFYUI --state /caminho/upload-exclusivo.json

Esse comando valida execução concluída, grafo08, manifesto, legendas, imagem1080×1080 e bytes da saída ComfyUI; faz um upload e registra a mídia validada. O CLI postiz upload direto do Marca Salão está bloqueado; não usar caminho interno do CLI ou HTTP alternativo para contornar o validador. O hook de ferramentas rejeita DRAFT com mídia não registrada e criação repetida para a mesma mídia/canal. Usar id/path devolvidos pelo validador nas ferramentas MCP. Se o hook bloquear, resolver a proveniência/duplicação; não contornar.

Revisão de campanha existente deve ATUALIZAR os mesmos IDs, nunca chamar criação como se fosse campanha nova. Consultar estado, conteúdo e anexo antes de repetir. Para atualização autorizada, usar o procedimento REST de upsert existente (type=draft, republish=false, value[].id igual ao ID existente), preservando grupo/canal e validando contagem/IDs após cada atualização. Se o método não puder preservar IDs, parar. Remover duplicados somente se houver pedido explícito, após confirmar os dois registros preservados e fazer cópia privada do estado anterior.

A imagem gerada deve ser comparada visualmente às referências aprovadas, além dos hashes. O guard valida proveniência, não substitui a avaliação visual. Não editar a imagem completa com ferramenta local. Nenhuma correção autoriza publicação/agendamento. A data editorial usa a data efetiva do pedido em America/Sao_Paulo; não inferir agendamento a partir de datas preenchidas num DRAFT.
