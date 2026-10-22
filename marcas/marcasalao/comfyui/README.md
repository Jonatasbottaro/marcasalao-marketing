# Workflow Marca Salão para ComfyUI

Fonte do workflow e exportador para Hermes; leia [HERMES-POSTIZ.md](HERMES-POSTIZ.md). Pacote não publica, não agenda nem cria rascunho no Postiz.

Dois workflows: geração Gemini ou imagem local. Uma imagem de apoio resulta em seis variantes (Facebook/Instagram em quadrado, vertical e Stories), duas legendas e manifesto com hashes.

Template em verde-petróleo/menta/branco, logo oficial preservada. Os valores hex são escolhas do template, não códigos oficiais da marca.

Testes: `python3 -m unittest discover -s tests -v` (Python + Pillow). O código dos nós depende também do ambiente ComfyUI já instalado; não há modelos locais.

Implantação no Servidor02 depende de backup central confirmado, build incremental e atualização exclusiva do recurso ComfyUI. Confira o estado real da instalação na documentação operacional do servidor; presença dos arquivos no repositório não comprova implantação.

Padrão vigente: **salão realista v2**, aprovado em 21/10/2026 a partir do post Facebook 122109973515500502. Cenário fotográfico com mármore, plantas e dourado, logo central, título branco/menta e até três benefícios. O nó `MarcaSalaoGeminiCenario` incorpora a referência; logo e textos são aplicados localmente. Legendas explicativas com emojis, chamada por rede, pergunta e hashtags. O exemplo financeiro é apenas uma prévia comparativa; não criar publicação repetida.
