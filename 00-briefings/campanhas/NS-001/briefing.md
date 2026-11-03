# Briefing de campanha

> Briefing piloto da Content Factory, preenchido a partir de [`../../TEMPLATE-BRIEFING.md`](../../TEMPLATE-BRIEFING.md). Este documento **não** é roteiro, legenda, arte nem registro de publicação. Ele registra a dor, a evidência disponível e os limites de promessa de uma campanha futura.
>
> Validação técnica que sustenta esta versão: [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md) — leitura de código e testes selecionados do repositório `Jonatasbottaro/Salao02`, commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee`.
>
> Classificação usada em todo o documento: **confirmado** (sustentado por evidência consultada), **hipótese** (plausível, sem comprovação), **pendente de validação** (precisa ser testado antes da produção).

## 1. Identificação

- Código: NS-001
- Nome: Organização e visibilidade da agenda
- Responsável: pendente de definição (não há responsável documentado no repositório)
- Data de criação: 2026-11-02
- Data de atualização: 2026-11-02
- Status: em validação
- Versão: 0.2

## 2. Objetivo da campanha

- Objetivo principal: apresentar como uma agenda organizada ajuda o salão a visualizar e acompanhar os atendimentos, usando o Marca Salão como demonstração concreta somente nos comportamentos validados. A descoberta de horários disponíveis não faz parte deste objetivo: a validação técnica localizou essa capacidade no fluxo público do cliente, não na agenda do gestor ([`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md), seções 5 e 9).
- Resultado esperado: gerar interesse em conhecer a agenda do Marca Salão e solicitar uma demonstração.
- Canal ou canais: proposta inicial — Instagram Stories, Instagram Reels, YouTube Shorts, TikTok; WhatsApp Status se compatível com a estratégia já documentada. Nenhum canal foi publicado; nada aqui registra publicação realizada.
- Formato ou formatos: proposta — peça vertical com captura real da agenda e narração em texto separado, conforme [`../../../WORKFLOW.md`](../../../WORKFLOW.md). Definição final pendente de roteiro e edição.

Não prometer: redução de faltas, aumento de faturamento, aumento de ocupação, preenchimento de horários, resultado operacional garantido.

## 3. Público

- Público principal: pessoas responsáveis pela gestão de salões de beleza.
- Segmento: pequenos negócios do setor de beleza que ainda controlam horários de forma manual ou fragmentada; responsáveis pela organização da agenda e dos atendimentos.
- Contexto de uso: acompanhar os atendimentos marcados ao longo do dia, da semana e do mês, e localizar um atendimento na tela quando necessário.
- Nível de conhecimento sobre o Marca Salão: não documentado — tratar como hipótese.

Não há no repositório pesquisa, censo ou dado sobre o público. Idade, renda, quantidade de salões, número de usuários e comportamento de compra **não** foram levantados e não devem ser afirmados na campanha sem fonte.

## 4. Dor principal

- Dor: dificuldade de visualizar e acompanhar os agendamentos do salão com clareza.
- Pergunta principal: "Você consegue visualizar os agendamentos do seu salão com clareza?"
- Situação em que ocorre: a gestão precisa acompanhar atendimentos marcados ao longo do dia, da semana e do mês, e nem sempre tem essa leitura reunida em uma única tela.
- Como o público descreveria essa dor: a pergunta acima, formulação permitida como pergunta de reconhecimento. Não afirmar que todos os salões possuem esse problema.
- Frequência ou recorrência: não medida.
- Evidência disponível: nenhuma pesquisa quantitativa localizada no material consultado ([`../../../docs/historico/2026-11-02-apresentacao-sistema-salao02.md`](../../../docs/historico/2026-11-02-apresentacao-sistema-salao02.md), [`../../../04-legendas/`](../../../04-legendas/), [`../../../marcas/marcasalao/posts/`](../../../marcas/marcasalao/posts/)). A capacidade técnica correspondente está em [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md), seções 4 e 5.
- Hipóteses ainda não validadas: que a falta de visibilidade da agenda aumente o esforço de gestão; que o salão perceba isso como problema próprio; que a leitura reunida em uma tela reduza esse esforço.

### Formulação anterior — descartada para esta versão

- **Texto anterior (histórico, não usar como mensagem atual):** "Você sabe quais horários ainda estão disponíveis no seu salão?"
- **Motivo da rejeição:** a validação funcional classificou a oferta de horários disponíveis e a exibição de slots livres como **não suportadas na agenda do gestor**. Manter essa pergunta como mensagem atual implicaria atribuir à tela do gestor uma capacidade que existe apenas no fluxo público do cliente.
- **Estado:** hipótese rejeitada; descrita aqui para preservar o histórico da campanha.

> Não foi localizada, no material consultado, uma pesquisa quantitativa que comprove frequência, volume ou impacto financeiro da dor.

## 5. Impacto

- Impacto operacional: dificuldade de visualizar a distribuição dos atendimentos; maior esforço para acompanhar a agenda; dificuldade para planejar a rotina. Descritos como consequências qualitativas da dor, não como medição.
- Impacto financeiro: **hipótese, sem valores.** Um horário sem atendimento pode representar uma oportunidade de receita não realizada, mas o impacto depende do serviço, do preço, da duração, da procura e da possibilidade de reagendamento.
- Impacto na experiência do cliente: não avaliado — pendente.
- Impacto na equipe: não avaliado — pendente.
- Consequência de não agir: a gestão continua dependendo de anotações ou memória para acompanhar o que já está registrado; formulação qualitativa, sem dado.

Não inventar: ticket médio, quantidade de faltas, prejuízo mensal, percentual de ocupação, retorno sobre investimento. Nenhum número aparece neste briefing e nenhum deve aparecer na campanha sem fonte identificável.

## 6. Solução proposta

- Abordagem: centralizar e visualizar os agendamentos em uma agenda do sistema, limitada aos comportamentos efetivamente confirmados na validação.
- Como o Marca Salão participa: oferece uma tela de agenda no painel do salão ([`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md), seção 4). A criação de agendamentos e o cálculo de disponibilidade existem no **fluxo público do cliente**; essas capacidades não pertencem à tela autenticada da agenda do gestor, e por isso não podem ser apresentadas como se estivessem nela.
- O que depende do estabelecimento: registrar corretamente os agendamentos; manter os dados atualizados; acompanhar os horários; estabelecer o próprio processo de contato com clientes; administrar cancelamentos, confirmações e remarcações pelos meios adotados pelo salão.
- Limitações de contato com o cliente: **O Salao02 contém implementação técnica de notificações e lembrete de 24 horas, mas implantação, configuração dos canais e entrega real não foram validadas para esta campanha. A NS-001 não está autorizada a prometer ou demonstrar essas capacidades.** Não há comprovação de prevenção de faltas. Qualquer ação efetiva sobre o cliente — avisar, confirmar, remarcar — depende do salão e dos meios que ele usar.
- O que não será prometido: ver seção 8.

## 7. Funcionalidade usada como prova

- Funcionalidade: Agenda do Marca Salão (painel do salão, item de menu "Agendamentos", rota `/gestor/agenda`).
- Onde está disponível: no painel do gestor. A rota foi conferida por leitura de código no commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee` do repositório `Jonatasbottaro/Salao02` (`src/app/(dashboard)/gestor/agenda/page.tsx`, registrada em `ROUTE_MAP.md`). A leitura arquivada em 18/10/2026 ([`../../../marcas/marcasalao/posts/2026-10-18-organizacao-agenda-equipe/README.md`](../../../marcas/marcasalao/posts/2026-10-18-organizacao-agenda-equipe/README.md)) já citava o mesmo arquivo.
- Documento de validação: [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md).

### Confirmado no código

Sustentado pela leitura do commit auditado. Nada desta lista foi aberto em navegador:

- visão dia;
- visão semana;
- visão mês;
- agendamentos ocupados;
- filtro por profissional;
- filtro por status;
- busca por nome do cliente;
- detalhes;
- horário;
- cliente;
- profissional;
- serviço;
- preço no modal;
- status;
- confirmação;
- conclusão;
- no-show;
- cancelamento;
- pagamento local;
- exportação CSV.

Elementos também visíveis na captura consultada, por [`../../../01-insta-stories/05_agenda.png`](../../../01-insta-stories/05_agenda.png) (arquivo registrado no Git em 02/10/2026 pelo commit `a6e7f79` "Substitui imagens por capturas reais do site marcasalao.com.br com conta demo"; a própria tela exibe a data "Sexta, 02 De Out 2026" e o ambiente "Studio Bella – Demonstração"): cabeçalho "AGENDA DO SALÃO"; subtítulo "Acompanhe os atendimentos por período, profissional e status."; controles de navegação de data; seletor "Dia", "Semana", "Mês"; campo "Buscar cliente"; selects "Todos os profissionais" e "Todos status"; grade de horário com marcador "08:00"; controle "Exportar CSV"; item de menu "Agendamentos".

### Confirmado por testes automatizados

Alcance mais estreito que o anterior: são comportamentos isolados, executados com mocks ou em jsdom, durante a auditoria. Não equivalem a executar a aplicação:

- alternância entre as visões semana e mês (`src/components/agenda/AgendaViewSwitcher.test.tsx`);
- regras isoladas de agendamento na biblioteca — criação, pagamento pendente, conclusão e espera de pagamento (`src/app/(public)/booking/_lib/__tests__/bookings.test.ts`);
- cancelamento e recusa entre tenants (`src/app/api/bookings/cancel/route.test.ts`);
- regras isoladas do lembrete de 24 horas, com envio mockado (`src/lib/notifications/booking-reminders.test.ts`).

### Pendente de execução autenticada

Nenhum item abaixo foi observado em tela:

- renderização real da agenda;
- login e autorização;
- carregamento dos dados;
- ação real dos filtros de profissional e status no navegador;
- busca de cliente no navegador;
- abertura do modal de detalhes;
- efetivação das ações de status;
- conteúdo gerado por "Exportar CSV";
- integração entre o agendamento público e a agenda do painel;
- comportamento em celular;
- estado atual da tela — a captura registrada no repositório é de 02/10/2026;
- significado operacional de cada valor do filtro de status.

### Não suportadas na agenda do gestor

Verificadas como ausentes na tela autenticada do gestor, no commit auditado:

- slots disponíveis;
- oferta de horários livres;
- criação;
- edição;
- remarcação;
- exclusão;
- duração como campo próprio;
- preenchimento automático.

A criação de agendamentos e o cálculo de disponibilidade existem no fluxo público do cliente. Essas capacidades não pertencem à tela autenticada da agenda do gestor analisada nesta validação.

### Fluxo público de agendamento — evidência separada

Por verificação documentada em [`../../../marcas/marcasalao/posts/2026-10-18-como-funciona-agendamento/README.md`](../../../marcas/marcasalao/posts/2026-10-18-como-funciona-agendamento/README.md): a sequência identificação → serviço → profissional → data/horário → resumo antes da confirmação foi confirmada no código `src/app/(public)/booking/_components/BookingWizard.tsx` e na entrada pública `https://marcasalao.com.br/booking/demo-studio-bella`. Isso comprova o fluxo do cliente, **não** o comportamento da agenda do gestor — e não autoriza apresentar disponibilidade como recurso da tela do gestor.

### Notificações e lembrete de 24 horas — formulação técnica vigente

O Salao02 contém implementação técnica de notificações e lembrete de 24 horas, mas implantação, configuração dos canais e entrega real não foram validadas para esta campanha. A NS-001 não está autorizada a prometer ou demonstrar essas capacidades.

- **Versão anterior, substituída (histórico, não usar como afirmação atual):** "o sistema não envia mensagens, lembretes ou confirmações automáticas". A leitura do commit auditado localizou implementação, scheduler, rota interna e testes aprovados, o que torna a formulação absoluta imprecisa. Detalhes em [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md), seção 7.
- **Efeito prático para a campanha:** a proibição de usar mensagens, lembretes ou confirmações como promessa permanece integralmente válida. Não houve mudança de autorização — houve mudança na precisão técnica do motivo.

Uma captura de tela comprova apenas o que está visível nela. Ela não comprova que um botão funciona, que um filtro filtra, que uma exportação exporta, nem que a agenda do painel reflete os agendamentos feitos pela página pública.

## 8. Mensagem

- Mensagem principal: "Tenha mais clareza sobre os agendamentos do seu salão."
- Promessa permitida: "Acompanhe os agendamentos do dia, da semana ou do mês em uma agenda organizada."
- Versão anterior da mensagem, **descartada** (mantida como histórico): "Tenha mais clareza sobre os horários ocupados e disponíveis do seu salão." Rejeitada porque a oferta de horários disponíveis não é capacidade da agenda do gestor; a formulação atual fala só de agendamentos.
- Afirmações que precisam de comprovação antes de uso: "veja todos os horários disponíveis"; "controle toda a agenda"; "evite conflitos de horário"; "reduza faltas"; "melhore o faturamento"; "aumente a ocupação". As quatro primeiras já têm resposta negativa ou parcial na validação — ver seções 7 e 9 de [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md).
- Palavras ou expressões recomendadas: organizar, visualizar, acompanhar, clareza, rotina, agenda do salão — sempre ligadas a comportamento confirmado.
- Palavras ou expressões proibidas: automático; lembrete automático; confirmação automática; fim das faltas; zero no-show; faturamento garantido; agenda sempre cheia; nunca mais perca clientes; elimine horários vagos; "o Marca Salão reduz suas faltas"; "Nunca mais tenha clientes faltando"; "Envie lembretes automáticos"; "Confirme clientes automaticamente"; "Acabe com o no-show"; "Preencha automaticamente os horários vagos".
- Objeções do público: não levantadas com clientes — registrar como pendência de escuta real. Hipóteses de objeção (mudança de rotina, custo, medo de perder o controle do contato com o cliente) não podem virar texto de campanha sem validação.
- Respostas às objeções: dependem da validação acima; nenhuma resposta está aprovada nesta versão.

## 9. Estrutura do conteúdo

Estrutura alinhada à validação técnica. O roteiro aprovado nasce de outra etapa; nada aqui autoriza gravação.

- Hook: pergunta sobre a clareza com que a gestão visualiza os agendamentos do salão.
- Problema: dificuldade para acompanhar os atendimentos registrados.
- Consequência: maior esforço operacional e menor clareza da rotina.
- Solução: visualização organizada dos agendamentos na agenda do painel.
- Demonstração: visões dia, semana e mês, filtros por profissional e status, busca por cliente e detalhes do agendamento.
- Resultado esperado: mais clareza para acompanhar a rotina, sem garantia de redução de faltas ou de aumento de receita.
- CTA: "Conheça a agenda do Marca Salão."

Não associar nenhuma destas etapas a horários disponíveis, slots livres ou oferta de espaço na agenda: são capacidades do fluxo público do cliente, não da agenda do gestor (validação, seções 5 e 9).

### Formulação anterior — descartada para esta versão

- Hook anterior: "Você sabe quais horários ainda estão disponíveis no seu salão?" — **texto anterior, não usar como mensagem atual**; rejeitado pela evidência técnica, mantido como histórico em [`../../../02-hooks/campanhas/NS-001/hooks.md`](../../../02-hooks/campanhas/NS-001/hooks.md).
- Consequência anterior: mencionava "identificar espaços disponíveis" — **descartada**; a dor atual é de acompanhamento e clareza, não de localizar lacunas.
- Demonstração anterior: "somente ações confirmadas na tela real da agenda", com a disponibilidade entre as pendências — **hipótese rejeitada**; a disponibilidade foi confirmada como ausente na agenda do gestor.

## 10. Materiais necessários

- Captura atual da agenda, revalidada na data da produção (a registrada no Git em 02/10/2026 é a única disponível).
- Validação da resolução e da legibilidade da captura no formato final do canal.
- Gravação de tela somente após validar o fluxo que será demonstrado.
- Elementos oficiais de marca existentes no repositório: identidade verde-petróleo, menta e branco, logo MS/tesoura, conforme as artes aprovadas em [`../../../marcas/marcasalao/posts/`](../../../marcas/marcasalao/posts/).
- Relação das telas adicionais necessárias: pendente da definição do fluxo validado.
- Fonte de qualquer dado que venha a ser utilizado: obrigatória; sem fonte, o dado não entra na peça.
- Proteção ou ocultação de dados pessoais em toda captura, ainda que em ambiente de demonstração.
- Narração em texto separado por cenas e tempos, legendas visíveis e `.srt` sincronizado; vídeo entregue sem áudio, conforme [`../../../WORKFLOW.md`](../../../WORKFLOW.md).

Não incluir captura com: dados reais de clientes, telefone, e-mail, informações pessoais, credenciais, dados sensíveis do estabelecimento. O acesso ao painel de demonstração não fica neste repositório; credenciais não entram em briefing, roteiro, captura ou legenda.

## 11. Canais e adaptações

Proposta inicial, não material publicado. Duração final pendente de roteiro e edição; não definir duração universal sem evidência.

### Canal 1

- Canal: Instagram (Stories e Reels)
- Formato: vertical
- Proporção: padrão do repositório para peças verticais — conferir antes de fixar
- Duração: pendente de roteiro
- Tom: direto e educativo, sem jargão técnico
- CTA: "Conheça a agenda do Marca Salão." + orientação de link na bio, somente se o link externo do perfil estiver confirmado na data da publicação
- Adaptações necessárias: legenda própria; URL não é clicável em legenda do Instagram; botão desenhado em imagem não gera adesivo de link

### Canal 2

- Canal: YouTube Shorts e TikTok
- Formato: vertical
- Proporção: pendente de confirmação por canal
- Duração: pendente de roteiro
- Tom: idem
- CTA: idem, ajustado ao que cada canal permite
- Adaptações necessárias: verificar política de link e formato vigente antes de produzir

### Canal 3

- Canal: WhatsApp Status — apenas se compatível com a estratégia já documentada
- Formato, proporção, duração, tom e CTA: pendentes de definição

Facebook: se entrar na campanha, usar URL completa na legenda com a chamada padrão do projeto; registrar aqui antes de produzir.

## 12. CTA

- CTA principal: "Conheça a agenda do Marca Salão."
- Destino: [`https://marcasalao.com.br`](https://marcasalao.com.br) — endereço oficial documentado e aprovado no repositório. O painel de demonstração (`https://marcasalao.com.br/gestor`) também está documentado, mas exige credenciais que não ficam neste repositório: não prometer acesso direto sem combinar o acesso com o responsável pelo projeto.
- Ação esperada: acessar a apresentação do sistema ou solicitar uma demonstração.
- Como será rastreado: pendente — não há mecanismo de rastreamento definido no repositório. Sem mecanismo definido, registrar como não rastreado, não como "sem resultado".

## 13. Métricas

Métricas pretendidas, sem meta numérica: visualizações, alcance, retenção, cliques, solicitações de demonstração, conversões quando houver definição válida.

- Objetivo de medição: entender se a peça gera interesse em conhecer a agenda.
- Visualizações / alcance / retenção / cliques / solicitações de demonstração / conversões: linha de base ainda não disponível.
- Período de medição: pendente de definição junto com o canal.
- Fonte dos dados: pendente — depende do rastreamento da seção 12.

Nenhuma meta numérica foi criada. Nenhuma métrica realizada foi preenchida: não há publicação desta campanha.

## 14. Riscos e restrições

- Riscos de mensagem: confundir organização da agenda com prevenção automática de faltas; usar o termo no-show como se o sistema resolvesse a causa sozinho; apresentar hipótese como fato; prometer resultado financeiro; atribuir à agenda do gestor a exibição de horários disponíveis, que pertence ao fluxo público do cliente.
- Riscos de promessa indevida: usar mensagens, lembretes ou confirmações como argumento comercial; sugerir preenchimento automático de horários vagos; garantir aumento de ocupação ou de faturamento. A proibição comercial se mantém mesmo depois de a auditoria ter localizado implementação técnica de reminder — ver seção 7 deste briefing e seção 7 de [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md).
- Dependências: execução autenticada da agenda em ambiente local com emuladores e dados fictícios; captura atualizada; definição de responsável; política de CTA por rede já registrada em [`../../../AGENTS.md`](../../../AGENTS.md). A leitura de código e os testes selecionados já foram feitos e estão registrados em [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md); o que falta é a confirmação de comportamento executado.
- Restrições técnicas: vídeo sem áudio, com legendas queimadas e `.srt` correspondente; narração entregue como texto separado.
- Restrições de marca: identidade verde-petróleo, menta e branco; sem tela fictícia; sem simular botão clicável em imagem estática; não republicar para corrigir legenda.
- Risco de material herdado: existem textos antigos neste repositório que tratam automação de contato como capacidade comercial já disponível — por exemplo [`../../../04-legendas/roteiro_enviar_link.md`](../../../04-legendas/roteiro_enviar_link.md) ("sua agenda atualiza no automático 24 horas por dia") e [`../../../templates/youtube_horizontal/index.html`](../../../templates/youtube_horizontal/index.html) ("Automatize o envio de lembretes aos clientes"). São rascunhos/template históricos, não referência de qualidade; não devem ser reutilizados nesta campanha. A auditoria localizou implementação técnica de reminder no produto, mas isso **não** reabilita esses textos: implantação, configuração dos canais e entrega real seguem pendentes e a promessa comercial continua não autorizada. Nenhum desses arquivos foi alterado nesta tarefa.
- Risco de formulação herdada fora deste escopo: a afirmação absoluta de que o sistema não possui mensagens ou lembretes automáticos ainda aparece em [`../../README.md`](../../README.md), [`../../../02-hooks/README.md`](../../../02-hooks/README.md) e [`../../../03-roteiros/README.md`](../../../03-roteiros/README.md), arquivos que esta tarefa não modifica. Fica registrada como pendência editorial; a formulação técnica vigente é a da seção 7.
- Pendências: ver seções 7, 8, 12 e 16.

## 15. Checklist de validação

- [ ] A dor é real e compreensível.
- [x] O público está definido.
- [x] O impacto não foi inventado.
- [ ] A funcionalidade existe no sistema atual.
- [ ] A funcionalidade foi verificada.
- [ ] As capturas correspondem ao comportamento descrito.
- [x] O conteúdo não promete mensagens automáticas.
- [x] O conteúdo não promete lembretes automáticos.
- [x] O conteúdo não promete resultados garantidos.
- [x] A responsabilidade do estabelecimento está clara quando aplicável.
- [x] O CTA está definido.
- [ ] As métricas estão definidas.
- [ ] As pendências críticas foram resolvidas.
- [ ] O briefing foi aprovado antes da produção.
- [ ] A demonstração mostra somente comportamentos confirmados.
- [ ] Nenhum dado pessoal aparece nas capturas.
- [ ] A mensagem não apresenta organização da agenda como prevenção automática de faltas.

Os itens marcados referem-se ao texto deste briefing. A validação por leitura de código e testes selecionados existe e está registrada em [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md), mas ela não preenche estes checkboxes: "existe no sistema atual" e "foi verificada" exigem execução autenticada, responsável definido e data de validação no ambiente em uso; as capturas ainda são a única de 02/10/2026; e as pendências críticas continuam abertas. O briefing permanece **não aprovado**.

## 16. Aprovação

- Elaborado por: assistente de marketing do Marca Salão, a partir de [`../../TEMPLATE-BRIEFING.md`](../../TEMPLATE-BRIEFING.md), sob solicitação do titular em 2026-11-02
- Revisado por: pendente de definição
- Aprovado por: pendente
- Data da aprovação: pendente
- Observações: briefing em validação; produção não autorizada até a execução autenticada da agenda em ambiente local com emuladores e dados fictícios. A versão 0.2 incorpora a validação técnica registrada em [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md) e remove dos textos atuais qualquer associação entre a agenda do gestor e horários disponíveis. Este documento não autoriza publicar, agendar ou gerar materiais. Estados e critério de pronto em [`../../README.md`](../../README.md).
