# Multitrack Hub — ComfyUI, Gemini e Postiz

Configuração exclusiva de Multitrack Hub, aprovada em 22/10/2026. Uma arte quadrada por campanha, compartilhada entre Facebook e Instagram; duas legendas. Sem modelos locais. Configurar o fluxo não cria campanhas, rascunhos, agendamentos ou publicações.

## Identidade e fatos

Referências: artes publicadas de apresentação e rateios, logo oficial em M formado por sete pistas de áudio e fontes do repositório https://github.com/swnsolucoes/Multitrack. CSS oficial: artifacts/multitrack-hub/src/index.css; identidade: docs/contexto/LOGO-MULTITRACKHUB.md. Ciano #00FFFF, fundo #09090B, cartões #121216, branco #FAFAFA e fonte Inter. Ambiente musical, pistas e formas de onda. Preservar a identidade própria, sem copiar cenário, tesoura ou contatos de outras marcas.

Consultar o produto antes de afirmar funcionalidades, condições de rateios, preços, disponibilidade ou direitos. Não prometer ganho financeiro ou licenciamento não comprovado. Site https://multitrackhub.com.br. Sem WhatsApp/telefone. Na imagem usar CTA neutra e domínio; não simular botão clicável.

## Execução econômica

Antes de executar, consultar /object_info no ComfyUI e confirmar MultitrackHubBrief, MultitrackHubArteIA e MultitrackHubPacoteIA. Se algum estiver ausente, informar instalação pendente e não usar workflows de outra marca como substituição.

Workflows na pasta Multitrack Hub:
- 10-multitrackhub-criar-anuncio: MultitrackHubBrief → MultitrackHubArteIA → MultitrackHubPacoteIA. Uma chamada de imagem Gemini 2K, proporção 1:1; exportação RGB 1080×1080, sem recorte ou recomposição local.
- 11-multitrackhub-reutilizar-arte: brief → LoadImage → pacote. Arte completa existente, zero chamadas Gemini.

CLI exclusivo:

    python3 /dados/aplicacoes/comfyui-servidor02/multitrackhub_export.py --brief /caminho/brief.json --state /caminho/estado-novo.json --output /caminho/pacotes

Modelo: exemplo-brief-multitrackhub.json. Para reutilizar acrescentar --square-art /caminho/arte.png. Consultar execução pendente com --resume /caminho/estado.json --output /caminho/pacotes, sem reenviar. Não apagar estado, trocar campanha ou aumentar revisão para contornar erro. Cache concluído com hash válido reutiliza a imagem; estado incerto bloqueia repetição automática. Falha ou baixa qualidade exige revisão antes de nova chamada paga. Chave somente no ambiente privado do Coolify.

Saídas em /data/output/multitrackhub/. Pacote tem brand=multitrackhub, visual_standard=multitrackhub-quadrado-ia-v1, uma imagem e duas legendas; postiz.media_by_network aponta ambas para o mesmo PNG. publication_authorized=false, review_required=true, draft_only. O manifesto não é payload de publicação. Nenhum nó ou exportador acessa Postiz.

## Legendas e encaminhamento

Escrever textos próprios para cada rede, claros e factuais: abertura, benefício explicado, orientação, pergunta final e poucas hashtags. Facebook recebe URL completa do site ou /rateios conforme destino. Instagram usa link na bio somente se o link externo estiver confirmado no perfil atual; caso contrário @multitrackhub. Não inserir uma URL clicável fictícia na arte.

Conferir visualmente logo, texto, acentos, fidelidade dos fatos e contraste. Uma resposta bem-sucedida da API não comprova qualidade. Apresentar a arte e ambas as legendas para revisão.

O perfil Hermes exclusivo é /home/swn/.hermes/profiles/multitrackhub-marketing. Ler COMFYUI-MULTITRACKHUB.md e POSTIZ-OPERACAO.md nesse perfil. Pedidos somente de prévia não autorizam upload ou rascunhos. Quando o titular pedir o processo completo ou rascunhos, consultar histórico e temas reservados SOMENTE desta marca, escolher um tema ainda não utilizado, gerar uma arte e duas legendas e criar dois DRAFT sem publicação. Sem recorrência automática.

Canais exclusivos: Facebook cmvbss5fn0005msbhhbdy6ing; Instagram cmvbsudg50007msbh2j4734i4. Confirmar integrationList e schemas atuais antes de gravar. Um upload compartilhado e dois rascunhos com legenda correspondente. Verificar anexos, estado DRAFT e releaseURL/releaseId nulos. Preservar outros registros. Publicar ou agendar exige autorização específica; não usar type now/schedule como teste.

## Recuperação

Fonte no Servidor02: /dados/aplicacoes/comfyui-servidor02. O rollback da imagem Docker restaura o serviço anterior; remover somente os novos arquivos de workflow da pasta Multitrack Hub após salvá-los se necessário. Não remover saídas, caches ou estados de geração. Backup e procedimentos oficiais em /dados/Backup/servidores/servidor02-remoto/documentacao/Servidor02.
