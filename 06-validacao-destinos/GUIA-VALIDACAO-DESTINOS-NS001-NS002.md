# Guia Operacional — Validação de Destinos das Campanhas NS-001 e NS-002

## 1. Contexto e escopo

Este guia permite que outra pessoa valide um destino **antes de aprovar uma peça para publicação**. O objetivo é garantir que cada CTA de cada peça aponte para um destino clicável confirmado, funcional, e que o comportamento do destino (redirecionamentos, preservação de UTMs, ação oferecida) esteja alinhado ao CTA prometido na peça.

O escopo cobre documentação, modelos e ensaio local com dados fictícios. Publicação, envio de formulários, criação de contas e alterações no site, no Postiz ou no analytics ficam fora deste trabalho.

Consultas a destinos públicos podem ser feitas em modo de leitura, sem inserir UTMs de teste em produção.

## 2. Matriz de destinos — NS-001 e NS-002

Preencha uma linha por combinação de campanha + peça/formato + canal. Quando o material apresentar opções, registre cada opção como candidata e indique a decisão pendente.

### Colunas

| Coluna | Descrição |
| --- | --- |
| `campanha` | `ns-001` ou `ns-002` |
| `peca_ou_formato` | Identificador da peça ou formato (ex.: `NS-001-P001-reels`, `NS-002-P001-stories`) |
| `canal` | `instagram`, `facebook`, `youtube`, `tiktok`, `whatsapp` |
| `cta` | Texto do CTA usado na peça |
| `posicionamento` | `legenda`, `bio`, `sticker`, `descricao`, `nenhum` |
| `destino_candidato` | URL do destino candidato (ex.: `https://marcasalao.com.br`) |
| `status_aprovacao` | `aprovado`, `pendente_de_decisao`, `rejeitado` |
| `evidencia` | Fonte da evidência (briefing, roteiro, AGENTS.md, confirmação do titular) |

### Matriz preenchida (dados de campanha, não de ensaio)

| campanha | peca_ou_formato | canal | cta | posicionamento | destino_candidato | status_aprovacao | evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ns-001 | NS-001-P001-reels | instagram | "Conheça a agenda do Marca Salão." | legenda | https://marcasalao.com.br | pendente_de_decisao | briefing NS-001 seção 12; roteiro 001 cena 7 |
| ns-001 | NS-001-P001-stories | instagram | "Conheça a agenda do Marca Salão." | bio | https://marcasalao.com.br | pendente_de_decisao | briefing NS-001 seção 11 Canal 1 |
| ns-001 | NS-001-P001-shorts | youtube | "Conheça a agenda do Marca Salão." | descricao | https://marcasalao.com.br | pendente_de_decisao | briefing NS-001 seção 11 Canal 2 |
| ns-001 | NS-001-P001-status | whatsapp | "Conheça a agenda do Marca Salão." | nenhum | (sem destino clicável) | pendente_de_decisao | briefing NS-001 seção 11 Canal 3 |
| ns-002 | NS-002-P001-reels | instagram | "Conheça o agendamento online no Marca Salão" | legenda | https://marcasalao.com.br | pendente_de_decisao | briefing NS-002 seção 12; roteiro 001 cena 6 |
| ns-002 | NS-002-P001-reels | instagram | "Conheça o agendamento online no Marca Salão" | bio | https://marcasalao.com.br | pendente_de_decisao | briefing NS-002 seção 11 Canal 1 |
| ns-002 | NS-002-P001-stories | instagram | "Conheça o agendamento online no Marca Salão. marcasalao.com.br" | sticker | https://marcasalao.com.br | pendente_de_decisao | briefing NS-002 seção 11 Canal 2 |
| ns-002 | NS-002-P001-reels | facebook | "Conheça o agendamento online no Marca Salão" | descricao | https://marcasalao.com.br | pendente_de_decisao | briefing NS-002 seção 11 Canal 3 |

### Regras da matriz

- `destino_candidato` é `https://marcasalao.com.br` para todas as peças com destino clicável, conforme destino oficial documentado em `AGENTS.md` ("Chamadas para o site Marca Salão").
- O painel de demonstração (`https://marcasalao.com.br/gestor`) exige credenciais: **não** usar como destino público de campanha.
- Quando o CTA é "link na bio" ou sticker, o destino é o link cadastrado na bio/perfil, não necessariamente `marcasalao.com.br` diretamente — confirmar com o titular antes de publicar.
- Todas as linhas acima estão `pendente_de_decisao` até o titular confirmar destino, CTA por canal e link externo cadastrado no perfil.

## 3. Teste de aceite do caminho completo

Antes de aprovar uma peça, execute o seguinte teste para cada destino candidato:

### 3.1 Passos do teste

| Passo | Ação | Critério de aceite |
| --- | --- | --- |
| 1 | Abrir o destino em navegador de celular (modo de leitura, sem preencher formulários) | Página carrega sem erro de DNS, TLS ou 404 |
| 2 | Conferir a página final após todos os redirecionamentos | URL final é a esperada; não há redirecionamento inesperado para página diferente do prometido |
| 3 | Verificar preservação dos UTMs quando aplicáveis | Se o destino usa UTMs, eles chegam ao servidor (verificar nos logs de acesso ou analytics); se não usa UTMs, confirmar que não são exigidos |
| 4 | Confirmar que a ação oferecida corresponde ao CTA | O que o usuário pode fazer na página final está alinhado com o CTA da peça (ex.: CTA "conheça a agenda" → página apresenta a agenda/sistema; CTA "conheça o agendamento online" → página apresenta o fluxo de agendamento) |

### 3.2 Registro do teste

Preencha uma linha por destino testado no modelo `modelo-teste-aceite-destino.csv`.

| Coluna | Descrição |
| --- | --- |
| `campanha` | `ns-001` ou `ns-002` |
| `destino_candidato` | URL testada |
| `data_hora_teste` | Data e hora do teste, ISO 8601 com fuso |
| `dispositivo` | `celular`, `desktop` |
| `navegador` | Nome e versão do navegador |
| `url_final_apos_redirects` | URL final após todos os redirecionamentos |
| `redirects_esperados` | `sim` ou `nao` |
| `utms_preservados` | `sim`, `nao` ou `nao_aplicavel` |
| `acao_corresponde_cta` | `sim` ou `nao` |
| `status_teste` | `aprovado`, `reprovado`, `pendente` |
| `observacoes` | Observações sobre falhas, redirecionamentos, divergências |

## 4. O que pode ser medido em cada ponto

| Ponto da jornada | O que pode ser medido | Fonte | Status |
| --- | --- | --- | --- |
| Clique na peça (rede social) | Cliques reportados pelo canal no link/bio/sticker | Painel nativo da rede social ou ferramenta de gestão de mídia | Disponível quando a plataforma reporta |
| Chegada ao site | Sessões, visualizações de página, origem do tráfego | Analytics do site (ex.: Google Analytics, Meta Pixel) | **Não configurada neste escopo** — pendência |
| Conversão confirmada | Preenchimento de formulário, solicitação de demonstração | Analytics do site + evento de conversão configurado | **Não configurado** — sugerir apenas quando houver ação correspondente documentada |

### Evento de conversão sugerido

Sugira um evento de conversão **apenas quando houver uma ação correspondente documentada** na campanha. Por exemplo:
- Se a peça leva para `marcasalao.com.br` e há um formulário de "solicitar demonstração" documentado no site, o evento de conversão pode ser `formulario_demonstracao_enviado`.
- Se não há ação correspondente documentada, não sugerir evento de conversão; registrar como pendência.

### Medições ainda não comprovadas

Registre como pendência qualquer medição que ainda não tenha fonte confirmada:
- Mecanismo de rastreamento (utm, pixel) — não definido
- Analytics do site — não configurado
- Fonte de dados para coleta de métricas — não definida

## 5. Ensaio local (redirecionamento em localhost)

O ensaio valida o fluxo de validação de destinos executando um teste HTTP em **localhost** com duas rotas de redirecionamento fictícias. Não consulta a bio real nem destinos de produção; todos os dados são fictícios.

### 5.1 Como reproduzir o teste

1. Inicie um servidor de teste local com três rotas:
   - `GET /redirect-passa?<utms>` — responde `302` encaminhando a query string (os quatro UTMs) para `/destino`.
   - `GET /redirect-descarta?<utms>` — responde `302` descartando a query string, redirecionando para `/destino` sem parâmetros.
   - `GET /destino` — espelha a query string recebida no corpo da resposta.
2. Acesse cada rota de redirecionamento com a **mesma entrada** de UTMs (ex.: `utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1`).
3. Siga o redirecionamento até o destino final (`/destino`).
4. Compare os parâmetros recebidos no destino final com os parâmetros de entrada.
5. Se os parâmetros coincidem → preservados (`sim`). Se faltarem → não preservados (`nao`).

### 5.2 Cenários do ensaio

| Cenário | Destino testado | Tipo de link |
| --- | --- | --- |
| `redirecionamento_passa` | `http://127.0.0.1:8765/redirect-passa?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1` | Redirecionamento que encaminha UTMs |
| `redirecionamento_descarta` | `http://127.0.0.1:8765/redirect-descarta?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1` | Redirecionamento que descarta query string |
| `sem_link_clicavel` | (nenhum) | Sem link clicável |

### 5.3 Preservação de UTMs na bio real e medição no site

A preservação de UTMs em cliques de link de **bio real** e a medição de chegada/conversão no **site** **não foram verificadas neste ensaio**. O ensaio roda somente em `localhost` com rotas fictícias. Registre como **pendente de verificação** quando houver acesso à bio real e ao analytics do site.

### 5.4 Registro do ensaio

Preencha o modelo `ensaio-validacao-destinos.csv`.

| Coluna | Descrição |
| --- | --- |
| `campanha` | `ns-001` ou `ns-002` |
| `cenario` | `redirecionamento_passa`, `redirecionamento_descarta`, `sem_link_clicavel` |
| `destino_testado` | URL inicial testada no ensaio |
| `data_hora_teste` | Data e hora do teste, ISO 8601 com fuso |
| `url_final_apos_redirects` | URL final após seguir os redirecionamentos |
| `utms_preservados` | `sim`, `nao` ou `nao_aplicavel` |
| `acao_corresponde_cta` | `sim` ou `nao` |
| `resultado_esperado` | O que se espera do teste |
| `resultado_observado` | O que foi observado (resultado do localhost) |
| `acao_se_falhar` | Ação necessária se a validação falhar |
| `status_teste` | `aprovado`, `reprovado`, `pendente` |

### 5.5 Linhas do ensaio (resultados do localhost)

| campanha | cenario | destino_testado | data_hora_teste | url_final_apos_redirects | utms_preservados | acao_corresponde_cta | resultado_esperado | resultado_observado | acao_se_falhar | status_teste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ns-001 | redirecionamento_passa | http://127.0.0.1:8765/redirect-passa?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1 | 2026-11-17T10:00:00-03:00 | http://127.0.0.1:8765/destino?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1 | sim | nao_aplicavel | Os quatro UTMs de entrada chegam ao destino final | Os quatro UTMs de entrada chegaram ao destino final (localhost). | — | aprovado |
| ns-001 | redirecionamento_descarta | http://127.0.0.1:8765/redirect-descarta?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1 | 2026-11-17T10:05:00-03:00 | http://127.0.0.1:8765/destino | nao | nao_aplicavel | Nenhum UTM de entrada chega ao destino final | Nenhum parâmetro chegou ao destino final (query string descartada no redirecionamento). | Tratar como perda de rastreamento; investigar rota de redirecionamento. | reprovado |
| ns-001 | sem_link_clicavel | (nenhum) | 2026-11-17T10:10:00-03:00 | (nenhum) | nao_aplicavel | nao | Sem destino clicável; CTA apenas de texto | Nenhum destino para testar; CTA é de texto apenas. | — | pendente |

### 5.6 Interpretação dos resultados

- **redirecionamento_passa:** aprovado. O redirecionamento encaminhou os quatro UTMs ao destino final; a checagem confirma a preservação.
- **redirecionamento_descarta:** reprovado. O redirecionamento descartou a query string; nenhum UTM chegou ao destino final. A checagem detecta a perda de rastreamento.
- **sem_link_clicavel:** pendente. Não há destino para testar; o CTA é apenas de texto. `utms_preservados = nao_aplicavel`.

## 6. Decisões que o Jonatas precisa tomar antes da primeira publicação

| Decisão | Detalhe | Por que é necessária |
| --- | --- | --- |
| Destino clicável confirmado por campanha | Confirmar se `https://marcasalao.com.br` é o destino para todas as peças ou se há destino diferente por canal | Sem destino confirmado, não há como validar nem parametrizar links |
| Link externo cadastrado na bio/perfil do Instagram | Confirmar qual URL está cadastrada na bio do perfil @marcasalao | Necessário para peças com CTA "link na bio" (NS-001 Stories, NS-002 Reels/Stories) |
| Uso de sticker de link nos Stories (NS-002) | Autorizar ou não o sticker de link; confirmar se o link externo está cadastrado | Sticker requer autorização separada de publicação |
| UTMs do perfil para bio compartilhada | Definir se UTMs são exigidos no link de bio ou se o clique na bio é aceitável sem rastreamento por UTM | **Pendente de verificação:** não há evidência real sobre preservação de UTMs em links de bio compartilhados; o ensaio de localhost não testa a bio real. |
| Mecanismo de rastreamento (utm, pixel) | Definir qual mecanismo será usado para rastrear cliques e conversões | Sem rastreamento, não é possível medir eficácia das peças |
| Analytics do site configurado | Confirmar se analytics do site está ativo para medir chegada e conversão | Sem analytics, não há como confirmar conversão após o clique |
| Evento de conversão documentado | Definir qual ação no site representa conversão (ex.: solicitar demonstração) | Sem evento definido, não há conversão a medir |
| CTA por canal | Confirmar o CTA exato para cada canal (legenda, bio, sticker, descrição) | Cada canal tem regras próprias sobre o que é clicável |
| Aprovação dos briefings NS-001 e NS-002 | Aprovar os briefings antes de qualquer produção ou publicação | Briefings não aprovados bloqueiam produção e publicação |

## 7. Arquivos entregues

| Caminho | Conteúdo |
| --- | --- |
| `06-validacao-destinos/GUIA-VALIDACAO-DESTINOS-NS001-NS002.md` | Este guia operacional |
| `06-validacao-destinos/modelo-matriz-destinos.csv` | Modelo vazio para matriz de destinos |
| `06-validacao-destinos/modelo-teste-aceite-destino.csv` | Modelo vazio para teste de aceite de destino |
| `06-validacao-destinos/ensaio-validacao-destinos.csv` | Exemplo preenchido (ensaio, dados fictícios) |

## 8. Limites

- Não publicar, não enviar formulários, não criar contas, não alterar o site, o Postiz ou o analytics.
- Consultas a destinos públicos em modo de leitura apenas; sem UTMs de teste em produção.
- Este guia prepara a validação; a execução real depende de autorização do titular.
