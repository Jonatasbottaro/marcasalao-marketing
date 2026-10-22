# Marca Salão — arte integral IA v3 — ComfyUI, Hermes e Postiz

## Padrão vigente

O titular pediu aplicar a criação integral por IA após rejeitar o acabamento da composição local. O padrão de novas criações é **arte-integral-ia-v3**, com referência visual no post https://www.facebook.com/photo/?fbid=122109973515500502 e prompt reverso adaptável em custom_nodes/servidor02_gemini/assets/padrao-arte-integral.txt.

Fluxo: brief e legendas verificáveis → roteiro completo com referência → Gemini gera seis peças completas em 2K (Facebook/Instagram × quadrado/vertical/Stories) → ajuste somente de escala, sem recortar ou redesenhar textos/logo → pacote com imagens, legendas e hashes → conferência visual humana → integração Postiz apenas quando solicitada. Nenhum modelo local.

O padrão anterior v2 (cenário Gemini + logo/textos Pillow) está preservado como legado nos workflows 04/05. Não usar 04/05 nem --background para as novas artes completas: eles podem reintroduzir o acabamento rejeitado. Não aplicar texto sobre arte que já contém texto.

## ComfyUI

Antes de executar, conferir /object_info/MarcaSalaoArteIA e /object_info/MarcaSalaoPacoteIA no serviço. Se ausentes, a aplicação v3 ainda não foi concluída; não usar o legado como substituição silenciosa nem declarar a instalação concluída.

- Workflow visual/API padrão: 06-marcasalao-arte-integral-ia. Nós MarcaSalaoBriefIA, seis MarcaSalaoArteIA, MarcaSalaoPacoteIA.
- Workflow 07-marcasalao-reutilizar-artes-ia: seis arquivos completos existentes; sem Gemini.
- Primeira execução sem cache pode realizar **seis chamadas de imagem 2K**, uma por rede/formato. Não chamar de uma única geração de fundo. Cada proporção tem composição própria; não recortar o quadrado para vertical/Stories.
- Os nós salvam cada saída original, prompt e metadados em /data/output/marcasalao/geracoes-ia/<campanha>/<assinatura>/. Saídas completas com SHA válido são reutilizadas sem nova chamada. Estado incerto/incompleto bloqueia repetição automática.
- O campo revisao começa em 1. Para refazer somente uma arte após conferir o erro/resultado, aumentar revisao APENAS no nó correspondente. Isso autoriza uma chamada nova daquele nó; os demais continuam no cache. Não aumentar todos nem mudar campanha/prompt apenas para contornar timeout.
- Contrato de saída: manifest.json schema_version 1, visual_standard arte-integral-ia-v3, seis imagens RGB e duas legendas, status prepared, review_required true, publication_authorized false, postiz.mode draft_only, sem uploads/rascunhos criados.
- Alterar rede, formato ou revisão exige conferir o input real de cada nó; não supor que o título do nó define seu destino.

## Exportador local

Executar no Servidor02:

    python3 /dados/aplicacoes/comfyui-servidor02/marcasalao_export.py --brief /caminho/brief.json --state /caminho/estado-novo.json --output /caminho/pacotes

O arquivo state deve ser novo e é reservado antes de enviar o pedido. O padrão atual executa workflow06. --resume /caminho/estado.json consulta o mesmo prompt_id e exporta, sem reenviar geração. Em falha, ler histórico e metadados; não trocar o estado para forçar repetição. Nunca copiar a chave Gemini, que permanece no ambiente privado do Coolify.

Para reutilizar seis artes completas, acrescentar --artworks seguido de seis PNGs nesta ordem: Facebook quadrado, vertical, Stories, Instagram quadrado, vertical, Stories. O workflow07 apenas escala/exporta. --background é opção explicitamente LEGADA v2 para fundos sem texto; não usar com as artes novas.

## Brief e legendas

exemplo-brief.json tem os campos atuais. Preencher campanha com slug; tema, titulo e texto com conteúdo verificável. texto contém até três benefícios separados por | ou quebra de linha. direcao_visual descreve objetos/cenário relacionados ao tema. Não copiar finanças/benefícios antigos para campanhas diferentes.

Hermes escreve as legendas: abertura com benefício/emojis discretos; contexto; até três blocos com recurso e explicação concreta; orientação útil; pergunta final; três a cinco hashtags. Preencher legenda_facebook e legenda_instagram com esse corpo, sem chamada/URL: o compositor de LEGENDAS insere CTA antes da pergunta/hashtags. A exportação v3 não compõe elementos visuais, mas preserva esse tratamento textual das legendas.

Facebook: Acesse o link da descrição na arte e URL completa https://marcasalao.com.br na legenda. Instagram: Acesse o link na bio somente com confirmação do link externo real; sem confirmação, Conheça o Marca Salão e @marcasalao. A validação registrada em 19/10/2026 deve ser reavaliada se o perfil mudar. Não simular botão/adesivo clicável em imagem estática.

## Revisão obrigatória da arte completa

A IA também desenha letras, ícones e logo: conferir ortografia, acentos, nome da marca, monograma/tesoura, título, todos os benefícios, CTA da rede e endereço. Conferir mãos/objetos, contraste (benefícios brancos sobre parede verde, nunca mármore), proporção, áreas seguras e ausência de recortes. A existência do PNG ou sucesso da API não comprova qualidade visual. Não aprovar automaticamente nem criar posts de uma imagem defeituosa. Se necessário, refazer somente o nó correspondente, mantendo as outras saídas.

Apresentar a arte e a legenda integral para avaliação. Pode mostrar corpo comum e as chamadas distintas por rede, sem omitir pergunta e hashtags.

## Postiz — somente escopo autorizado

Prévia ou pedido de regenerar imagens autoriza gerar/exportar arquivos e mostrar resultados. Não autoriza upload, rascunho, agendamento ou publicação. Nenhum workflow/exportador faz chamadas Postiz.

Quando houver pedido de rascunhos, consultar POSTIZ-OPERACAO.md, confirmar canais com integrationList e consultar posts antes de criar para evitar duplicação. Somente Facebook cmvbegwql0001msbhvdpjy0in e Instagram cmvbeq3100003msbhihu2dm4z, ambos Marca Salão. Não tocar Multitrack Hub.

Escolher UMA variante de feed por rede, de preferência vertical; seis alternativas não são seis posts. Stories requer pedido específico. Verificar hashes/manifesto e fazer upload real pelo CLI /home/swn/.local/bin/postiz upload no ambiente privado existente. Consultar schemas atuais e criar com type draft. Reconsultar registro e mídia para confirmar DRAFT, releaseURL/releaseId nulos e arte/legenda corretas. O manifesto não é payload de criação e caminho local não é URL pública.

Após erro/timeout, consultar estado e posts antes de qualquer repetição. Preservar posts e rascunhos anteriores. Publicar/agendar requer autorização específica do conteúdo, canais e horário. Arquivar no checkout autorizado somente conforme escopo, sem afirmar push ou publicação não verificados.
