# Briefing de campanha — NS-002 Agendamento online no Marca Salão

> Proposta editorial preparada a partir de [`../../TEMPLATE-BRIEFING.md`](../../TEMPLATE-BRIEFING.md). Este documento **não** é hook, roteiro, legenda, arte, gravação nem registro de publicação. Ele registra a dor a validar, a jornada observada, as evidências e os limites de promessa da campanha.
>
> Contexto consultado: [`../../../AGENTS.md`](../../../AGENTS.md), [`../../../WORKFLOW.md`](../../../WORKFLOW.md), [`../../../docs/contexto/ESTADO-ATUAL.md`](../../../docs/contexto/ESTADO-ATUAL.md), [`../../README.md`](../../README.md), [`../NS-001/VALIDACAO-FUNCIONAL-AGENDA.md`](../NS-001/VALIDACAO-FUNCIONAL-AGENDA.md) e [`../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md`](../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md). O estado atual versionado registra a main em revisão anterior (`2c409676`); a base real desta branch foi conferida no Git: `origin/main` = `7e31cb7300f291fbcc85821900dfbaf837123ee7`.
>
> Classificação usada em todo o documento: **confirmado** (sustentado por evidência consultada), **hipótese** (plausível, sem comprovação) e **pendente de validação** (precisa de checagem antes da produção). Hipótese não vira argumento de venda.
>
> **Limite central:** a jornada demonstrada é a do agendamento. Pagamento aparece nas evidências apenas como **mock de teste**; não é benefício, promessa nem etapa a destacar na peça pública.

## 1. Identificação

- Código: NS-002
- Nome: Agendamento online no Marca Salão
- Responsável: pendente de definição (não há responsável documentado no repositório)
- Data de criação: 2026-11-16
- Data de atualização: 2026-11-16
- Status: em validação — aguardando aprovação do titular
- Versão: 0.1

## 2. Objetivo da campanha

- Objetivo principal: mostrar, para gestores de salões de beleza, que a cliente percorre um fluxo público de agendamento — escolhe serviço, profissional e horário disponível, confirma — e que esse mesmo atendimento aparece na agenda do salão. A NS-001 mostrou a visão do gestor; a NS-002 complementa com a perspectiva da cliente e a ligação entre as duas pontas.
- Resultado esperado: despertar interesse em conhecer o agendamento online do Marca Salão e gerar solicitações de demonstração. Expectativa, não garantia de ocupação, receita ou redução de faltas.
- Canal ou canais: proposta inicial — Instagram Reels, Instagram Stories e Facebook Reels. YouTube Shorts e TikTok ficam como extensão opcional, mediante decisão de canal e política de link.
- Formato ou formatos: peça vertical 9:16, sem áudio, com legendas visíveis sincronizadas, `.srt` correspondente e narração em texto separado em `04-legendas/`, conforme [`../../../WORKFLOW.md`](../../../WORKFLOW.md). Formato final depende de hooks e roteiro aprovados.

Não prometer: agenda sempre cheia, ocupação garantida, aumento de faturamento, redução de faltas, envio automático de mensagens, lembretes ou confirmações automáticas.

## 3. Público

- Público principal: pessoas que gerenciam salões de beleza — o mesmo público da NS-001, agora com foco no momento da reserva pela cliente.
- Segmento: pequenos negócios de beleza com rotina de agendamento; gestores responsáveis por organizar serviços, equipe e agenda.
- Contexto de uso: quando uma cliente procura um horário e o salão precisa transformar essa escolha em um atendimento visível na agenda.
- Nível de conhecimento sobre o Marca Salão: **hipótese** — não foi medido. Não afirmar que o público já conhece o sistema.

Não há pesquisa quantitativa no repositório sobre esse público. Idade, renda, porte do salão, volume de agendamentos e comportamento de compra não foram levantados e não devem aparecer como dado.

## 4. Dor principal

- Dor a validar: o gestor pode não ter uma leitura imediata de que o horário escolhido pela cliente já virou um atendimento registrado na agenda do salão.
- Situação em que ocorre: no intervalo entre a cliente escolher o horário e o salão conferir a agenda. A formulação descreve uma situação observável no fluxo, não uma estatística.
- Como o público descreveria essa dor: "Quando a cliente agenda, eu consigo ver isso na agenda do salão?" — pergunta de reconhecimento, não afirmação de dor universal.
- Frequência ou recorrência: **não medida**.
- Evidência disponível: a jornada local executada em 2026-11-05 comprovou que o agendamento criado no fluxo público aparece para cliente, gestor e profissional ([`../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md`](../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md), seções 1–2). Não há entrevista ou pesquisa que comprove que gestores sofrem com a desconexão.
- Hipóteses ainda não validadas: que a ausência dessa visibilidade gere retrabalho; que o gestor valorize ver a ponta da cliente; que a demonstração aumente a intenção de conhecer o produto.

> A dor está formulada como **hipótese a validar com o titular e, depois, com o público**. A funcionalidade é que está confirmada; a dor não.

## 5. Impacto

> Valores financeiros não devem ser inventados. Nenhum número aparece neste briefing sem fonte.

- Impacto operacional: **hipótese qualitativa** — sem a ligação visível entre escolha da cliente e agenda, o salão pode precisar conferir ou repassar informações manualmente. Não medido.
- Impacto financeiro: **sem dado disponível**. Horário não preenchido pode representar oportunidade não realizada, mas isso depende de preço, duração, procura e processo do salão; tratado como hipótese explícita, nunca como promessa.
- Impacto na experiência do cliente: **pendente de validação**. A jornada mostra que a cliente recebe confirmação na tela; não mede satisfação nem percepção.
- Impacto na equipe: **pendente de validação**. Não há dado sobre redistribuição de trabalho da equipe.
- Consequência de não agir: formulação qualitativa — a gestão continua sem uma leitura única entre o que a cliente escolheu e o que a agenda registra, quando esse fluxo não é usado. Sem dado de frequência ou custo.

## 6. Solução proposta

- Abordagem da solução: usar o fluxo público de agendamento do Marca Salão como prova de que a cliente consegue escolher serviço, profissional, data/horário disponível e confirmar; em seguida, mostrar o mesmo atendimento na agenda do gestor.
- Como o Marca Salão participa: oferece a rota pública `/booking/[salonId]` e a agenda autenticada `/gestor/agenda`. A integração entre as duas pontas foi observada na jornada E2E local de 2026-11-05.
- O que depende do processo do estabelecimento: cadastrar serviços ativos, ter profissional aprovado e vinculado ao serviço, manter dados de horário atualizados e decidir como trata pagamento e contato com a cliente.
- Limitações: validação feita em emuladores locais, com dados fictícios e pagamento mock; sem staging, produção, aparelho físico ou entrega real de notificações. Não há evidência para prometer envio automático, confirmação automática, lembrete, redução de faltas ou resultados comerciais.
- O que não será prometido: pagamento como benefício, disponibilidade garantida, automações de contato, ocupação, faturamento e desempenho em produção.

## 7. Funcionalidade usada como prova

- Funcionalidade: fluxo público de agendamento (`/booking/[salonId]`) integrado à agenda do gestor (`/gestor/agenda`).
- Onde está disponível no sistema: na aplicação Salao02. A auditoria de código identificou a superfície pública em `src/app/(public)/booking/`, a rota do gestor em `src/app/(dashboard)/gestor/agenda/page.tsx`, o cálculo de disponibilidade em `src/app/api/public/availability/route.ts` e a seleção de horário em `DateTimeSelection.tsx` ([`../NS-001/VALIDACAO-FUNCIONAL-AGENDA.md`](../NS-001/VALIDACAO-FUNCIONAL-AGENDA.md), seções 4, 5 e 8). Reconferência pontual de código no repositório `Jonatasbottaro/Salao02`, HEAD `91bb5e0cb0d9412ed186737b6b2e1c1f51f49a58`, nos arquivos `e2e/tests/local/full-user-journey.spec.ts`, `e2e/helpers/select-booking-slot.ts` e `docs/runbooks/local-full-user-journey-e2e.md`; clone temporário feito dentro de `<RAIZ>/.workspace/clones/`, removido ao final.
- Comportamento verificado: na jornada local de 2026-11-05, a cliente preencheu nome/sobrenome/telefone, escolheu serviço e profissional, selecionou o primeiro par data/horário disponível, confirmou o agendamento com pagamento mock e viu o agendamento em `/cliente/bookings`; o mesmo serviço apareceu em `/gestor/agenda` e o documento do agendamento ficou vinculado ao profissional.
- Evidência da verificação: [`../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md`](../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md), seções 1, 2 e 5; capturas técnicas em `../NS-001/capturas/2026-11-05/` cobrem a ponta do gestor, não a ponta da cliente.
- Captura ou demonstração necessária: nova fixture editorial e novas capturas da ponta da cliente e da agenda do gestor; ver plano na seção 10.
- Responsável pela validação: execução de 2026-11-05 feita pelo agente de marketing sob solicitação do titular. Responsável pela rodada NS-002: pendente de definição.
- Data da validação: 2026-11-05 para a jornada local; 2026-11-16 para a reconferência de código no HEAD `91bb5e0`.

Uma captura comprova somente o que aparece nela. A jornada E2E comprova a sequência no ambiente local; não comproba implantação, produção, aparelho real ou entrega de notificações.

### 7.1 Etapas observadas da jornada e evidência

| # | Etapa observada | Afirmação permitida na campanha | Evidência | Ambiente que sustenta | Classificação e limite |
| --- | --- | --- | --- | --- | --- |
| 1 | A cliente abre a página pública do salão em `/booking/[salonId]`. | "A cliente acessa uma página de agendamento do salão." | Código da rota pública em `src/app/(public)/booking/[salonId]/page.tsx`; E2E navega para `/booking/{salonId}?service={serviceId}`. | Salao02 HEAD `91bb5e0`; E2E local de 2026-11-05. | Confirmado no código e executado localmente. Acesso sem login e deep link com parâmetro `client` permanecem pendentes. |
| 2 | Identificação: "Primeiro, seus dados" com Nome, Sobrenome e Telefone. | "A cliente informa seus dados na tela." | `completePublicClientIdentification` em `full-user-journey.spec.ts`, com os rótulos "Nome", "Sobrenome", "Telefone" e o botão "Continuar para o agendamento". | Chromium/Playwright local, 2026-11-05. | Confirmado por E2E. Na peça, usar somente dados fictícios. |
| 3 | Escolha de serviço: tela "Escolha um Serviço" e clique no cartão do serviço. | "A cliente escolhe o serviço." | `createBooking` no mesmo spec; serviço criado e editado pelo gestor no próprio teste. | Emuladores locais + app local. | Confirmado por E2E. O nome do serviço na peça deve vir da fixture editorial, não do E2E. |
| 4 | Escolha de profissional: cartão do profissional aprovado. | "A cliente escolhe o profissional." | `createBooking`; profissional vinculado e aprovado no teste. | Emuladores locais + app local. | Confirmado por E2E. Depende de configuração prévia do salão. |
| 5 | Escolha de data e horário: varredura de dias e seleção do primeiro slot habilitado. | "A cliente escolhe uma data e um horário disponíveis." | `selectFirstAvailableDateTime` varre botões de dia e horários `HH:MM` habilitados; `availability` e `DateTimeSelection.tsx` citados na auditoria. | Chromium local; regra calculada no código. | Confirmado por E2E no ambiente local. Regras internas de disponibilidade (pausas, feriados, antecedência) são confirmação de código, não foram todas exercitadas em tela nesta rodada. |
| 6 | Resumo e "Confirmar Agendamento". | "A cliente confirma o agendamento." | `createBooking` clica em "Continuar" e "Confirmar Agendamento". | Chromium local com pagamento mock. | Confirmado por E2E. Pagamento mock é evidência de teste; não entra como promessa nem como benefício. |
| 7 | Mensagem de sucesso após a confirmação. | "A interface confirma que o agendamento foi realizado." | Asserção no spec para "agendamento foi realizado com sucesso". | Chromium local. | Confirmado por E2E. Não afirmar envio de e-mail, SMS, WhatsApp ou push. |
| 8 | Agendamento visível para a cliente em `/cliente/bookings`. | "A cliente consegue ver o agendamento na área dela." | E2E navega para `/cliente/bookings` e localiza o serviço. | Chromium local. | Confirmado por E2E. A captura editorial correspondente ainda não existe. |
| 9 | Agendamento visível na agenda do gestor em `/gestor/agenda`. | "O mesmo atendimento aparece na agenda do salão." | E2E navega para `/gestor/agenda` e localiza o serviço; verificação manual de 2026-11-05 descreve visão Dia/Semana/Mês e capturas técnicas. | Chromium local; app em `http://localhost:5100`, viewport 390 × 844 na verificação manual. | Confirmado por E2E e por navegador autenticado local. Capturas antigas são técnicas, não frames aprovados. |
| 10 | Documento do agendamento vinculado ao profissional. | "O agendamento fica associado ao profissional escolhido." | Asserção no spec sobre `professionalId` em `appointments`. | Firestore Emulator. | Confirmado por E2E em emulador. Não prova produção. |
| 11 | Conclusão e avaliação ao final da jornada. | Não usar como promessa da NS-002. | E2E marca atendimento como concluído e envia avaliação. | Firestore Emulator. | Confirmado em teste, mas fora do escopo dos três momentos desta campanha. |

### 7.2 Ambiente das evidências

- Execução de 2026-11-05: estação Windows local, checkout do Salao02 citado no documento original — caminho absoluto não reproduzido aqui, por exigência de portabilidade —, Firebase Auth Emulator em `localhost:9099`, Firestore Emulator em `localhost:8080`, aplicação local em `http://localhost:5100` via `next start`, Chromium Playwright 1.58.2, viewport móvel emulado 390 × 844. Namespace fictício `e2e-1793884270981`; salão "Meu Salão E2E"; nenhum dado real, credencial, token ou sessão registrado.
- Limite do documento original: o checkout executado não possuía metadados Git verificáveis; por isso a execução comprova o ambiente observado, não identidade exata com o commit auditado `6342a33a36b0a4eadd0f5a62770f1eee485156ee`.
- Reconferência de código em 2026-11-16: repositório público `Jonatasbottaro/Salao02`, HEAD `91bb5e0cb0d9412ed186737b6b2e1c1f51f49a58`, somente leitura, dentro de `<RAIZ>/.workspace/clones/`; nenhum emulador, servidor, pagamento ou gravação executado nesta rodada.
- Não houve acesso a staging, produção ou aparelho físico. Nenhuma notificação externa foi exercitada.

### 7.3 Evidências que faltam ou precisam de grupo novo

- **Não era necessário repetir a jornada nesta rodada:** a prova local de 2026-11-05 já cobre a sequência cliente → agenda do gestor. A reconferência de código serviu para checar o fluxo no remoto atual, não para substituir a execução.
- Capturas da ponta da cliente em fixture editorial: pendentes.
- Confirmação da jornada em um checkout com metadados Git verificáveis e alinhado a um commit explícito do Salao02: pendente para a etapa de produção.
- Verificação de acesso sem conta e do deep link com parâmetro `client`: pendente; não usar como promessa.
- Comprovação de pagamento real, produção, aparelho físico e entrega de notificações: pendente e fora do escopo da NS-002.

## 8. Mensagem

- Mensagem principal: "A cliente escolhe o horário. O salão vê o agendamento na agenda."
- Promessa permitida: "No fluxo validado localmente, a cliente escolhe serviço, profissional e horário disponível, confirma o agendamento e o atendimento aparece na agenda do gestor."
- Afirmações que precisam de comprovação: acesso sem conta; link público por salão; funcionamento em produção; pagamento real; notificações; redução de faltas; aumento de ocupação ou faturamento.
- Palavras ou expressões recomendadas: "escolhe", "confirma", "aparece na agenda", "fluxo validado localmente", "agendamento online", "acompanhe".
- Palavras ou expressões proibidas: "garantido", "sempre", "automático", "o sistema envia", "lembrete", "agenda cheia", "aumento de faturamento", "redução de faltas", "sem erro", "qualquer horário".
- Objeções do público: "preciso configurar alguma coisa antes?"; "a cliente precisa criar conta?"; "isso funciona no celular?"; "o pagamento já está resolvido?".
- Respostas às objeções, dentro do permitido: "O serviço e o profissional precisam estar cadastrados e ativos no salão"; "o acesso sem conta ainda está pendente de confirmação"; "a validação em viewport móvel 390 × 844 foi feita em Chromium, não em aparelho físico"; "o pagamento observado foi mock de teste e não faz parte da promessa da peça".

## 9. Estrutura do conteúdo

- Hook: "Quando a cliente escolhe um horário, o salão consegue ver esse atendimento na agenda?"
- Problema: a escolha da cliente e a leitura do gestor precisam estar conectadas para que o agendamento seja acompanhado sem depender de anotação paralela. Hipótese a validar com o titular.
- Consequência: sem essa ligação visível, o gestor pode precisar conferir ou repassar a informação manualmente. Hipótese qualitativa, sem dado de frequência.
- Solução: fluxo público de agendamento do Marca Salão, com a cliente escolhendo serviço, profissional e horário disponível.
- Demonstração: três momentos obrigatórios, na ordem abaixo.

| Momento | O que mostrar | Tela/evidência | Limite |
| --- | --- | --- | --- |
| 1 — A cliente escolhe | Identificação com dados fictícios, cartão de serviço e cartão de profissional. | `/booking/[salonId]`; E2E etapas 2–4. | Não mostrar dados reais; não afirmar que a cliente dispensa conta sem confirmação. |
| 2 — A cliente confirma | Calendário com horário disponível selecionado e confirmação na interface. | `DateTimeSelection` + fluxo de confirmação; E2E etapas 5–7. | Pagamento mock fica nos bastidores da prova; não virar benefício nem cena de destaque. |
| 3 — O salão vê | O mesmo serviço/cliente/profissional aparecendo em `/gestor/agenda`. | Verificação manual e E2E etapa 9. | Usar captura nova com fixture editorial; não reaproveitar frames de validação E2E. |

- Resultado esperado: o gestor reconheça a continuidade entre a escolha da cliente e a agenda do salão e queira conhecer o fluxo. Não prometer resultado medido.
- CTA: "Conheça o agendamento online no Marca Salão. marcasalao.com.br" como texto principal; "link na bio" e sticker de link ficam como variantes condicionadas às confirmações de canal.

## 10. Materiais necessários

- Telas: `/booking/[salonId]` com identificação, serviço, profissional, data/horário e confirmação; `/cliente/bookings`; `/gestor/agenda`.
- Capturas: todas precisam ser refeitas para a NS-002. As capturas de 2026-11-05 são evidência técnica da ponta do gestor, com namespace E2E, menu administrativo amplo, enquadramento de validação e preço fictício de R$ 12.000,00; não são frames aprovados.
- Vídeos: peça vertical 1080 × 1920, 30 fps, sem faixa de áudio; exportação com `-an` quando houver FFmpeg.
- Elementos de marca: identidade do Marca Salão; confirmar nome de uso público antes das artes finais, pois a interface capturada exibe "Meu Salão".
- Narração: texto separado por cena e tempo em `04-legendas/`; áudio gerado fora do editor. Nenhum áudio é produzido nesta rodada.
- Legendas: visíveis e sincronizadas no vídeo, com `.srt` correspondente.
- Dados ou fontes: [`../NS-001/VALIDACAO-FUNCIONAL-AGENDA.md`](../NS-001/VALIDACAO-FUNCIONAL-AGENDA.md), [`../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md`](../NS-001/VALIDACAO-EXECUCAO-2026-11-05.md), `full-user-journey.spec.ts` e `select-booking-slot.ts` do Salao02 no HEAD `91bb5e0`.
- Outros materiais: fixture editorial de dados fictícios, ainda a criar.

### 10.1 Capturas a preparar

| # | Captura final | Finalidade | Precisa de fixture nova? | Observação |
| --- | --- | --- | --- | --- |
| 1 | Card de abertura da marca | Gancho sem produto | Não | Texto curto; sem promessa de resultado. |
| 2 | Tela "Primeiro, seus dados" | Momento 1 | **Sim** | Nome, sobrenome e telefone fictícios, plausíveis e sem dados reais. |
| 3 | Tela "Escolha um Serviço" | Momento 1 | **Sim** | Serviço fictício com nome, preço e duração plausíveis. |
| 4 | Seleção de profissional | Momento 1 | **Sim** | Profissional fictício aprovado e vinculado ao serviço. |
| 5 | Calendário e horário disponível | Momento 2 | **Sim** | Mostrar dia e horário selecionados; não exibir regras internas não validadas em tela. |
| 6 | Confirmação do agendamento | Momento 2 | **Sim** | Mensagem de sucesso da interface; não incluir cobrança como promessa. |
| 7 | Área da cliente com o agendamento | Ponte opcional | **Sim** | Confirmar se entrará no corte final; hoje é evidência, não obrigatoriedade de cena. |
| 8 | Agenda do gestor com o mesmo atendimento | Momento 3 | **Sim** | Enquadramento vertical, sem menu administrativo amplo, sem E2E namespace. |
| 9 | Card final de CTA | Fechamento | Não | "Conheça o agendamento online no Marca Salão. marcasalao.com.br"; sem botão clicível desenhado. |

A fixture editorial deve usar somente dados fictícios, campos completos, valores plausíveis e nomes neutros. Cada quadro precisa ser revisado quanto a dados pessoais, credenciais, console aberto, namespace de teste e coerência de marca.

## 11. Canais e adaptações

### Canal 1

- Canal: Instagram Reels.
- Formato: vídeo vertical, sem áudio, com legendas visíveis e `.srt`.
- Proporção: 9:16, 1080 × 1920.
- Duração: proposta 25–35 s, a definir no roteiro por leitura cronometrada.
- Tom: direto, para gestores; pergunta de reconhecimento seguida de demonstração.
- CTA: "Conheça o agendamento online no Marca Salão. marcasalao.com.br"; "link na bio" somente se o link externo do perfil for confirmado.
- Adaptações necessárias: sem botão clicível desenhado; URL em legenda não é clicável no Instagram.

### Canal 2

- Canal: Instagram Stories.
- Formato: sequência curta de telas, sem áudio.
- Proporção: 9:16, 1080 × 1920.
- Duração: três telas, uma ação por tela; tempo final no roteiro.
- Tom: mesma pergunta do Reels, com textos mais curtos.
- CTA: texto principal com frase e domínio; sticker de link somente com autorização de publicação.
- Adaptações necessárias: não inferir que botão desenhado cria sticker.

### Canal 3

- Canal: Facebook Reels.
- Formato: vídeo vertical, sem áudio, com legendas visíveis e `.srt`.
- Proporção: 9:16, 1080 × 1920.
- Duração: mesma do Reels, salvo decisão contrária.
- Tom: igual ao Instagram, com chamada por descrição.
- CTA: `https://marcasalao.com.br` na legenda com "Acesse pelo link da descrição".
- Adaptações necessárias: confirmar se a campanha entra no Facebook antes de produzir a versão.

## 12. CTA

- CTA principal: "Conheça o agendamento online no Marca Salão. marcasalao.com.br"
- Destino: `marcasalao.com.br`; URL completa `https://marcasalao.com.br` quando o canal exigir link por descrição.
- Ação esperada: o gestor acessar o site para conhecer o sistema ou solicitar demonstração. Não prometer acesso direto ao painel `/gestor`, que exige credenciais.
- Como será rastreado: pendente. Não há mecanismo de rastreamento definido; registrar como não rastreado até decisão.

Confirmar o link real cadastrado antes de prometer acesso. No Instagram, "link na bio" só quando o link externo estiver confirmado; sticker depende de autorização separada. URL desenhada em imagem não é botão clicável.

## 13. Métricas

Sem meta numérica obrigatória enquanto não houver histórico.

- Objetivo de medição: observar interesse em conhecer o agendamento online, sem inferir resultado comercial.
- Visualizações: linha de base ainda não disponível.
- Alcance: linha de base ainda não disponível.
- Retenção: linha de base ainda não disponível; aferir no roteiro quando houver corte definido.
- Cliques: linha de base ainda não disponível; depende de link/confirmação de canal.
- Leads: pendente de definição do que conta como lead.
- Solicitações de demonstração: pendente de canal de recebimento.
- Conversões: pendente de definição; não usar "conversão" como sinônimo de visualização.
- Período de medição: pendente.
- Fonte dos dados: pendente; não presumir Postiz ou qualquer ferramenta como fonte sem confirmação.

## 14. Riscos e restrições

- Riscos de mensagem: tratar a dor como medida; sugerir que a cliente sempre agenda sem conta; transformar pagamento mock em benefício.
- Riscos de promessa indevida: automações de contato, lembretes, confirmações automáticas, redução de faltas, ocupação garantida, aumento de faturamento, funcionamento em produção.
- Dependências: aprovação deste briefing; fixture editorial; novo ambiente local com emuladores; responsável de captura; definição de marca e canais.
- Restrições técnicas: validação em emuladores e Chromium; sem aparelho físico; sem staging/produção; sem credenciais no repositório; vídeo sem áudio.
- Restrições de marca: a interface exibe "Meu Salão" e a campanha usa "Marca Salão"; decisão pendente antes das artes finais.
- Pendências: ver seção 17.

## 15. Checklist de validação

- [ ] A dor é real e compreensível — formulada, mas ainda pendente de validação com o titular/público.
- [x] O público está definido — gestores de salões de beleza.
- [x] O impacto não foi inventado — somente hipóteses qualitativas rotuladas e "sem dado disponível".
- [x] A funcionalidade existe no sistema atual — código conferido no Salao02 HEAD `91bb5e0` e em documentos da NS-001.
- [x] A funcionalidade foi verificada — jornada E2E local de 2026-11-05, com dados fictícios.
- [ ] As capturas correspondem ao comportamento descrito — pendente da fixture editorial e das novas capturas.
- [x] O conteúdo não promete mensagens automáticas.
- [x] O conteúdo não promete lembretes automáticos.
- [x] O conteúdo não promete resultados garantidos.
- [x] A responsabilidade do estabelecimento está clara quando aplicável — cadastro de serviços, profissional aprovado, dados e processo próprio de contato.
- [x] O CTA está definido como proposta — depende de aprovação e confirmação de canal.
- [ ] As métricas estão definidas — linha de base e fontes pendentes.
- [ ] As pendências críticas foram resolvidas.
- [ ] O briefing foi aprovado antes da produção.

## 16. Aprovação

- Elaborado por: agente de marketing do Marca Salão, em 2026-11-16.
- Revisado por: pendente.
- Aprovado por: pendente.
- Data da aprovação: pendente.
- Observações: rascunho para apreciação do titular. Aprovação deste briefing não autoriza hooks, roteiro, gravação, renderização, agendamento nem publicação. A produção seguirá [`../../../WORKFLOW.md`](../../../WORKFLOW.md) e [`../../../AGENTS.md`](../../../AGENTS.md).

## 17. Decisões antes de hooks e roteiro

1. **Aprovar o enquadramento da NS-002** como complemento da NS-001: cliente escolhe o horário e o atendimento aparece na agenda do salão.
2. **Validar a dor formulada** — "quando a cliente agenda, o salão consegue ver isso na agenda?" — ou substituí-la por outra pergunta de reconhecimento.
3. **Aprovar os três momentos da demonstração** e decidir se a tela `/cliente/bookings` entra como ponte explícita ou permanece apenas como evidência.
4. **Aprovar o CTA principal** "Conheça o agendamento online no Marca Salão. marcasalao.com.br" e os destinos por canal; manter "link na bio" e sticker como variantes condicionadas.
5. **Decidir como tratar o pagamento mock**: omitido da peça pública, como está proposto, ou citado apenas como detalhe de teste — nunca como benefício.
6. **Confirmar o nome de marca para uso público** ("Marca Salão" vs. "Meu Salão" na interface) antes de qualquer arte ou captura final.
7. **Autorizar a criação da fixture editorial e das novas capturas** em ambiente local com emuladores e dados fictícios, além de indicar o responsável e o commit do Salao02 que será usado.
8. **Definir canais, rastreamento e linha de base de métricas**, ou registrar explicitamente "não rastreado" e "linha de base ainda não disponível".
9. **Autorizar a passagem para hooks e roteiro** — decisão separada de autorização de gravação, renderização e publicação.
