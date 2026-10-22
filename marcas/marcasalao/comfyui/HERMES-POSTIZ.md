# Marca Salão — ComfyUI → pacote → Hermes → Postiz

Esta entrega prepara imagens e metadados. Não faz upload ao Postiz, não cria rascunho, não agenda nem publica. Não contém chave Gemini nem Postiz. Usa o ComfyUI existente no Servidor02 em `http://127.0.0.1:8188`; a chave Gemini permanece no ambiente privado do Coolify.

## Workflows

- `workflows/04-marcasalao-gemini.json`: abrir no ComfyUI, preencher o nó **Marca Salão · Brief e texto** e executar. Uma chamada Gemini cria apenas a imagem de apoio; a composição aplica logo/textos localmente. Cada execução explícita pode consumir créditos. Não repetir após timeout sem consultar histórico.
- `workflows/05-marcasalao-imagem-local.json`: escolher imagem no nó LoadImage. Mesmo template e pacote, sem chamadas Gemini. A imagem será recortada centralmente; conferir se não corta pessoas/objetos importantes. Não é edição semântica nem envio de foto de referência ao Gemini.
- `*.api.json`: versões para a API do ComfyUI; não importar como workflow visual.

Campos: identificador de campanha (minúsculas, números/hífens), tema curto, título (até 88 caracteres), corpo (até 160), legendas próprias por rede, direção visual e confirmação do link da bio. Limites de caracteres não garantem encaixe: a largura real da fonte também é validada. Reduza palavras longas, títulos ou corpo quando necessário. Não inventar preços, recursos, estatísticas ou resultados. O operador/Hermes deve verificar as alegações no site antes de enviar o pedido. A legenda deve conter só o texto editorial: o fluxo acrescenta CTA/endereço por rede.

`link_bio_confirmado` começa em false. Só marcar true depois de conferir o link externo real em @marcasalao. Sem confirmação a arte usa “Conheça o Marca Salão”, sem prometer link na bio. Facebook usa “Acesse o link da descrição” e inclui `https://marcasalao.com.br` na legenda. Não desenhar botão clicável na imagem estática. Stories não incluem adesivo de link e requerem solicitação própria antes de postagem.

## Execução pelo Hermes no mesmo servidor

Pré-requisitos locais: Python 3 e Pillow (já presente no Servidor02). O comando não precisa de chave e não lê arquivos privados de credenciais. A instalação ativa do novo nó precisa ser concluída antes da execução.

Copie `exemplo-brief.json` para um arquivo novo e edite o conteúdo. Em novo pedido, use um estado novo:

```bash
python3 /dados/aplicacoes/comfyui-servidor02/marcasalao_export.py \
  --brief /caminho/brief.json \
  --state /caminho/jobs/campanha-001.json \
  --output /caminho/pacotes
```

Para usar imagem local, acrescente `--background /caminho/foto.png`. O comando faz upload somente ao ComfyUI local e dispensa Gemini. Estado existente é recusado, evitando reenvio involuntário. Depois de uma interrupção com prompt_id salvo, consultar/baixar sem gerar outra imagem:

```bash
python3 /dados/aplicacoes/comfyui-servidor02/marcasalao_export.py \
  --resume /caminho/jobs/campanha-001.json \
  --output /caminho/pacotes
```

Se estado ficou `submitting` sem prompt_id, consultar `/queue` e `/history` antes de nova tentativa: o servidor pode ter aceitado o pedido. Não repetir automaticamente chamadas pagas. Um erro de exportação deixa `.partial-*` para diagnóstico, sem entregar diretório final. Não substituir arte faltante por mídia antiga. O mesmo pacote já baixado não é sobrescrito.

## Conteúdo e contrato do pacote

A saída indica `package` com caminho absoluto no host. Diretório `marcasalao/<campanha>/<UTC>-<id>/`, único por execução. Contém:

- `arte-facebook-quadrado.png` e `arte-instagram-quadrado.png`: 1080 × 1080.
- `arte-facebook-vertical.png` e `arte-instagram-vertical.png`: 1080 × 1350.
- `arte-facebook-stories.png` e `arte-instagram-stories.png`: 1080 × 1920, texto principal em área central com margens superior/inferior ampliadas.
- `legenda-facebook.txt`, `legenda-instagram.txt`, `manifest.json`, `README.md`.

Todos os PNGs são RGB. O manifesto v1 identifica marca, campanha, origem da imagem, dimensões, SHA-256 de cada mídia e legenda, revisão obrigatória e permissão de publicação false. `status: prepared` não significa DRAFT persistido no Postiz. Não tratar `postiz` como payload REST/MCP pronto: contém somente orientação de consumo. O exportador verifica hashes/PNG/dimensões antes de finalizar o pacote. Os textos permanecem os informados: não há geração automática de alegações comerciais.

Cada campanha pode gerar seis variantes, mas elas não representam seis posts. Escolher UMA variante por rede para cada conteúdo; padrão sugerido vertical, quadrado como alternativa. Stories ficam fora do fluxo de feed até pedido específico. A imagem gerada é reaproveitada apenas entre as variantes da mesma execução.

## Integração com Postiz — etapa posterior

Somente depois de pedido explícito para criar rascunhos:

1. Ler `/home/swn/.hermes/POSTIZ-OPERACAO.md` e confirmar pacote/revisão/conteúdo correto. Não procurar ou copiar chaves.
2. Consultar `integrationList`. Restringir a Facebook `cmvbegwql0001msbhvdpjy0in` e Instagram `cmvbeq3100003msbhihu2dm4z`. A chave compartilhada NÃO isola marcas tecnicamente.
3. Consultar `integrationSchema` atual de cada canal. Não inferir o schema MCP a partir do manifesto nem trocar IDs por IDs Meta.
4. Escolher uma arte por rede. Conferir visualmente, conferir legenda e link externo do perfil antes de usar bio CTA. Fazer upload com `/home/swn/.local/bin/postiz upload /caminho/arte.png` no ambiente privado do perfil Marca Salão. Confirmar `id`, `path` HTTPS e status ready. Caminho de arquivo ComfyUI NÃO é URL pública para anexar.
5. Usar o `path` real retornado como mídia no MCP e `type: draft`, seguindo o schema atual. Antes de repetir timeout, consultar os posts existentes. Salvar e confirmar IDs/anexos/estado antes de afirmar criação.
6. Arquivar a variante escolhida, legendas e README sanitizado em `marcas/marcasalao/posts/AAAA-MM-DD-tema/` no checkout próprio, seguindo o guia Git local. Não arquivar logs, estado privado, chaves ou acervo integral.

Não usar `now`/`schedule` sem aprovação específica do conteúdo/destinos/horário. Este workflow não modifica anúncios pagos, Meta, outra marca ou o Hermes do Servidor01. A preparação atual não executa nenhuma etapa de escrita no Postiz.

## Identidade e limitações

Logo oficial em `assets/marcasalao-logo.png`, origem `https://marcasalao.com.br/icons/icon-512x512.png`, preservada sem redesenho pela IA. Cores do template são escolhas de composição baseadas na paleta documentada; não são alegadas como códigos hex oficiais. Fonte DejaVu Sans do sistema, instalada na imagem Docker. Texto, margens e logo são fixados por Pillow; o conteúdo da imagem Gemini varia e precisa de revisão. Templates não validam automaticamente a veracidade de alegações nem garantem conformidade com regras de anúncios de cada rede.

## Instalação e retorno

Fonte `/dados/aplicacoes/comfyui-servidor02`; a ampliação fica no pacote de nós já permitido `servidor02_gemini`, sem liberar custom nodes externos nem instalar modelos. Antes de atualizar serviço, executar e conferir o backup central instalado. Build incremental: `docker build -f Dockerfile.marketing -t comfyui-servidor02:0.42.1-marketing-v1-20261021 .`. Alterar somente a imagem do recurso ComfyUI no Coolify, preservando variáveis e volume, e reaplicar. Copiar os dois workflows visuais para o volume persistente de workflows já existente; o COPY da imagem sozinho não atualiza volume previamente criado.

Retorno: restaurar a referência anterior `comfyui-servidor02:0.42.1-gemini-20261021` no mesmo recurso Coolify, reaplicar e conferir `/system_stats` e nós Gemini. Preservar volume/pacotes/estado. Os novos workflows exigem a imagem nova; não executar na versão anterior. Não restaurar banco Coolify globalmente, não revogar chave e não desativar a conta de faturamento compartilhada com Salao02 v2. Nenhuma exclusão é necessária.

## Padrão aprovado — salão realista v2 — 21/10/2026

Referência obrigatória: https://www.facebook.com/photo/?fbid=122109973515500502 — arte e legendas originais em `marcas/marcasalao/posts/2026-10-18-gestao-financeira/` no checkout autorizado. O titular aprovou explicitamente este padrão visual e editorial. Substitui o template branco/abstrato v1 para novas criações.

- Use o workflow `04-marcasalao-gemini` com o nó `MarcaSalaoGeminiCenario`, que envia a referência pública aprovada à API Gemini. O nó genérico de imagem não incorpora essa referência. Não usar o v1 abstrato.
- Cenário realista de salão: verde-petróleo e menta, bancada de mármore, plantas, detalhes dourados e objetos relacionados ao tema. Cabeçalho central, logo oficial preservada, título branco/menta grande, até três benefícios com ícones e chamada textual inferior. A chamada não simula botão clicável. Gemini gera somente cenário sem letras, interfaces ou logo; composição local mantém identidade e textos.
- Campo `texto`: de um a três benefícios curtos, separados por ` | ` ou quebra de linha. Até 62 caracteres por benefício, limitado também ao encaixe em duas linhas. Reduzir texto se não couber; nunca truncar silenciosamente.
- As legendas devem seguir a estrutura da referência: abertura com benefício e emojis discretos; contexto da rotina do salão; até três blocos com emoji, nome do recurso e explicação concreta; orientação útil quando necessária; pergunta final; três a cinco hashtags pertinentes. Tom claro, acolhedor e profissional, sem promessas de lucro ou resultados garantidos.
- Hermes redige o corpo com base em fontes verificadas. Preencher `legenda_facebook` e `legenda_instagram` com esse corpo editorial, pergunta e hashtags; OMITIR a chamada e a URL, que o compositor insere antes da pergunta/hashtags. O workflow não inventa fatos nem gera legenda automaticamente a partir de um tema vazio.
- Facebook: chamada com URL completa https://marcasalao.com.br. Instagram: link na bio somente se confirmado; caso contrário, chamada para @marcasalao. A validação do perfil registrada em 19/10/2026 pode ser usada nesta prévia, mas deve ser reavaliada se o perfil mudar.
- Variar cena e conteúdo conforme campanha, mantendo este padrão. O exemplo financeiro serve para comparação visual, sem criar publicação repetida. Nunca alterar posts existentes para adequá-los ao padrão novo.
- Pedido de prévia autoriza gerar/exportar arquivos e mostrar arte + legenda integral. Não autoriza upload, rascunho, agendamento nem publicação no Postiz.
