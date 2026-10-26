# Multitrack Hub — pacote ComfyUI

Fonte instalada no Servidor02: /dados/aplicacoes/comfyui-servidor02. Este pacote mantém somente os arquivos específicos da Multitrack Hub; depende do módulo cliente Gemini e da instalação base existente. Não é uma instalação independente.

Leia HERMES-POSTIZ-MULTITRACKHUB.md. Workflows 10/11, uma imagem quadrada e duas legendas. Sem publicação automática. Credenciais não fazem parte deste pacote.

## Validação do acervo — 25/10/2026

Execute na raiz do repositório: `/usr/bin/python3 -B marcas/multitrackhub/comfyui/test_multitrackhub.py`. Os testes usam as fontes da própria marca e o cliente compartilhado arquivado em `marcas/marcasalao/comfyui`, com chamadas Gemini simuladas; não geram imagens pagas nem acessam Postiz.

O Dockerfile usa esta pasta como contexto e exige a imagem-base indicada já disponível localmente. Acrescenta o registro dos nós Multitrack sem substituir o módulo principal da base. A revisão do acervo não constrói/deploya contêineres nem altera a instalação ativa.
