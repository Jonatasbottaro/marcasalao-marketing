# Workflow Marca Salão — arte integral IA v3

Padrão atual: workflow06, brief/roteiro → seis artes completas Gemini 2K por rede/proporção → exportar PNGs sem redesenhar textos ou recortar → legenda por rede e manifesto → revisão. Workflow07 reutiliza seis artes prontas sem Gemini. Consulte HERMES-POSTIZ.md para comandos, custos/retomada e política Postiz.

Workflows04/05 e --background são legado v2, preservados para retorno e comparação. Não usá-los nas novas criações integrais.

Primeiro pacote pode consumir seis chamadas de imagem 2K. Saídas completas são armazenadas e reutilizadas; revisão por nó permite refazer só uma. Nenhum modelo local, credencial no código, upload Postiz ou publicação automática. O pacote continua com seis alternativas (quadrado/vertical/Stories por rede), duas legendas e hashes; seis alternativas não são seis posts.

Testes: python3 -m unittest discover -s tests -v (Python + Pillow). Presença dos arquivos não confirma implantação: conferir nós no serviço e documentação operacional do Servidor02.
