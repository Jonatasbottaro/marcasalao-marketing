# Roteiro 001 — Organização e visibilidade da agenda

- Campanha: NS-001
- Briefing: [../../../00-briefings/campanhas/NS-001/briefing.md](../../../00-briefings/campanhas/NS-001/briefing.md)
- Biblioteca de hooks: [../../../02-hooks/campanhas/NS-001/hooks.md](../../../02-hooks/campanhas/NS-001/hooks.md)
- Validação funcional: [../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md)
- Hook selecionado: NS-001-H15 (texto revisado)
- Status do briefing: em validação
- Status do hook: rascunho
- Status do roteiro: rascunho
- Versão: 0.2
- Aprovação: pendente
- Autorizado para gravação: não
- Autorizado para publicação: não
- Data de criação: 2026-11-02
- Data da revisão: 2026-11-02
- Responsável: pendente de definição, se não documentado

> **Este roteiro permanece como rascunho editorial. A gravação e a publicação não estão autorizadas. As cenas demonstrativas ainda dependem da execução autenticada em um ambiente local com emuladores e dados fictícios.**

---

## 1. Objetivo

Apresentar a importância de visualizar e acompanhar os agendamentos do salão com clareza e mostrar a agenda do Marca Salão **somente nos comportamentos confirmados** pela validação técnica registrada, depois de executados em ambiente autenticado.

Resultado pretendido: despertar interesse em conhecer a agenda e levar a pessoa a solicitar uma demonstração.

Este roteiro não promete: redução de faltas, prevenção de no-show, aumento de ocupação, aumento de faturamento, mensagens automáticas, lembretes automáticos ou confirmações automáticas. Também não apresenta como capacidade da agenda do gestor a exibição de horários disponíveis, a criação, a edição, a remarcação ou a exclusão de agendamentos — a validação técnica classificou esses itens como não suportados nessa tela ([`VALIDACAO-FUNCIONAL-AGENDA.md`](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md), seções 5 e 9).

## 2. Público

- Responsáveis pela gestão de salões de beleza.
- Responsáveis pela organização da agenda e dos atendimentos.
- Pequenos negócios do setor de beleza que ainda controlam horários de forma manual ou fragmentada.

**Hipótese ainda não pesquisada:** como esse público realmente acompanha a agenda hoje, com quais ferramentas e com que frequência. Nenhuma pesquisa com clientes foi localizada no material consultado; o que aparece aqui é formulação qualitativa do briefing, não dado.

## 3. Hook selecionado

- **ID:** NS-001-H15
- **Categoria:** curiosidade
- **Texto original:** "Quais informações, na agenda, ajudam a acompanhar os atendimentos sem reconstruir o dia de memória?"
- **Texto revisado (usado nas cenas):** "Você consegue visualizar os agendamentos do seu salão com clareza?"
- **Razão editorial da escolha:** é o hook existente cujo sentido exige o menor ajuste frente à evidência técnica — trata de acompanhar os atendimentos pela agenda, sem depender de disponibilidade, automação ou resultado financeiro. A seleção não declara desempenho: nenhum hook foi publicado ou medido.
- **Risco de interpretação:** ser lido como promessa de que a tela reúne informações que nunca foram registradas nela, ou como garantia de clareza.
- **Evidência utilizada:** capacidades de visualização confirmadas no código — rota `/gestor/agenda`, visões dia/semana/mês, filtros por profissional e status, busca por nome do cliente, modal de detalhes com horário, cliente, profissional, serviço, preço e status ([`VALIDACAO-FUNCIONAL-AGENDA.md`](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md), seção 4).
- **Validação ainda necessária:** execução autenticada da tela em ambiente local com emuladores e dados fictícios. Nada deste roteiro pode ser gravado antes disso.

**Seleção anterior — histórico.** A versão 0.1 deste roteiro usava o hook NS-001-H01, com a pergunta sobre horários ainda disponíveis, como texto da Cena 1. A evidência técnica classificou a disponibilidade como capacidade não suportada pela agenda do gestor, então aquela formulação foi **descartada** deste documento e permanece registrada apenas em [`../../../02-hooks/campanhas/NS-001/hooks.md`](../../../02-hooks/campanhas/NS-001/hooks.md), como texto original e histórico. Não usar como mensagem atual, texto de tela ou narração.

## 4. Formato proposto

- Formato: vídeo vertical, proposto — não produzido.
- Proporção: 9:16, sustentada pela documentação existente do repositório (`01-insta-stories/README.md` trata os assets como 1080x1920; `WORKFLOW.md` manda salvar PNG 1080x1920 e exportar 1080x1920 a 30fps).
- Canais possíveis: Instagram Reels e Stories, YouTube Shorts, TikTok.
- Duração final: pendente de leitura e edição; nenhuma duração é afirmada aqui.
- Demonstração: condicionada à execução autenticada em ambiente local com emuladores e dados fictícios.
- Produção: vídeo sem áudio, com legendas visíveis sincronizadas, `.srt` correspondente e narração entregue como texto separado, conforme [`../../../WORKFLOW.md`](../../../WORKFLOW.md).

Nada neste roteiro está agendado, gravado ou publicado.

## 5. Estrutura narrativa

```
Hook → Situação → Visões da agenda → Filtros e busca → Detalhes → Ação de status → CTA
```

- **Hook:** a pergunta de clareza do NS-001-H15 revisado.
- **Situação:** a informação do dia pode estar espalhada, e reuni-la consome tempo no meio do trabalho — dificuldade de acompanhar, não prejuízo.
- **Visões da agenda:** o mesmo registro visto por dia, semana e mês.
- **Filtros e busca:** recortar a listagem por profissional, por status e pelo nome do cliente.
- **Detalhes:** abrir um agendamento fictício e ver horário, cliente, profissional, serviço, preço e status.
- **Ação de status:** confirmar manualmente um agendamento fictício na própria tela.
- **CTA:** conhecer a agenda do Marca Salão.

## 6. Roteiro por cenas

### Cena 1 — Pergunta de clareza

- Objetivo: abrir com a pergunta sobre visualizar os agendamentos com clareza, sem mencionar horários disponíveis e sem prometer nada.
- Duração estimada: pendente de edição
- Visual: fundo na identidade da marca (verde-petróleo, menta e branco) com o texto da pergunta em destaque; sem tela de produto nesta cena.
- Texto na tela: "Você consegue visualizar os agendamentos do seu salão com clareza?"
- Narração: "Você consegue visualizar os agendamentos do seu salão com clareza?"
- Evidência utilizada: [../../../02-hooks/campanhas/NS-001/hooks.md](../../../02-hooks/campanhas/NS-001/hooks.md), hook NS-001-H15 (texto revisado); pergunta principal da seção 4 do briefing 0.2.
- Validação necessária: nenhuma para a pergunta em si; as cenas demonstrativas (3 a 6) dependem da execução autenticada.
- Risco: ser lido como garantia de que a tela revela algo que não foi registrado nela, ou como crítica à forma como o salão trabalha hoje.
- Status da cena: rascunho

### Cena 2 — Situação de informação espalhada

- Objetivo: mostrar a rotina em que a informação do dia não está reunida em um só lugar, e o esforço operacional disso.
- Duração estimada: pendente de edição
- Visual: anotações, conversa e planilha em telas separadas, sem marca de produto.
- Texto na tela: "Quando as informações ficam espalhadas, cada lugar mostra um pedaço do dia."
- Narração: "Quando uma parte da agenda fica no caderno, outra na conversa e outra na planilha, reunir as informações pode tomar tempo no meio do atendimento."
- Evidência utilizada: dor e impacto operacional qualitativos das seções 4 e 5 do briefing 0.2.
- Validação necessária: nenhuma, pois a cena não mostra o produto; o registro em múltiplos lugares é situação do salão, não comportamento do sistema.
- Risco: a situação é **condicional** — o texto começa com "quando" e só vale para o salão em que ela de fato ocorre. Não há pesquisa que sustente apresentá-la como realidade de todos os salões ou da maior parte deles, e o roteiro não pode ser lido dessa forma. A cena também não pode servir para classificar o estabelecimento como desorganizado, nem afirmar prejuízo, perda de clientes ou redução de faturamento.
- Status da cena: rascunho

### Cena 3 — Visões dia, semana e mês

- Objetivo: mostrar a mesma rotina em três granularidades de visualização.
- Duração estimada: pendente de edição
- Visual: seletor de visualização da agenda acionado entre "Dia", "Semana" e "Mês", com navegação de data; somente dados fictícios.
- Texto na tela: "O mesmo registro, visto por dia, semana ou mês."
- Narração: "Na agenda do painel, o registro é o mesmo: dá para olhar o dia, a semana ou o mês."
- Evidência utilizada: página da agenda do gestor, `AgendaViewSwitcher.tsx` e `CalendarGrid.tsx` no commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee`, registrados na seção 8 da validação funcional; controles também visíveis em [../../../01-insta-stories/05_agenda.png](../../../01-insta-stories/05_agenda.png).
- Validação necessária: comportamento confirmado no código e em teste automatizado selecionado (alternância entre semana e mês); execução autenticada no navegador ainda pendente, inclusive o estado atual da tela e a legibilidade em celular.
- Risco: apresentar a troca de visão como se já estivesse testada em uso real, ou sugerir que a agenda mostra o que não foi registrado nela.
- Status da cena: rascunho — pendente de execução autenticada

### Cena 4 — Filtros e busca

- Objetivo: mostrar como recortar a listagem por profissional, por status e pelo nome do cliente.
- Duração estimada: pendente de edição
- Visual: seletores "Todos os profissionais" e "Todos status" alterados e campo de busca por nome de cliente, com a listagem reagindo; somente dados fictícios.
- Texto na tela: "Filtrar por profissional, por status, ou buscar pelo nome."
- Narração: "Dá para filtrar por profissional, por status, ou buscar o nome de um cliente."
- Evidência utilizada: filtros por profissional e status e busca por cliente confirmados no código da agenda do gestor (seções 4 e 8 da validação funcional).
- Validação necessária: ação real dos filtros e da busca no navegador, pendente de execução autenticada; o significado operacional de cada valor do filtro de status ainda precisa ser conferido em tela. Não mostrar filtro inexistente nem busca por serviço ou por período que não esteja implementado.
- Risco: insinuar que a tela aponta disponibilidade, sugere horários ou encontra sozinha o que a pessoa procura; a consulta é feita pela pessoa.
- Status da cena: rascunho — pendente de execução autenticada

### Cena 5 — Detalhes de um agendamento fictício

- Objetivo: mostrar o que aparece ao abrir um agendamento na agenda do gestor.
- Duração estimada: pendente de edição
- Visual: modal de detalhes aberto sobre um agendamento fictício, exibindo horário, cliente fictício, profissional fictício, serviço fictício, preço fictício e status.
- Texto na tela: "Abrir um atendimento e ver os dados dele."
- Narração: "Abrindo o atendimento, aparecem o horário, o cliente, o profissional, o serviço, o preço e o status."
- Evidência utilizada: `BookingDetailModal.tsx` e os campos horário, cliente, profissional, serviço, preço e status registrados como confirmados no código (seções 4 e 8 da validação funcional).
- Validação necessária: abrir o modal em navegador autenticado, com dados fictícios, e conferir quais campos realmente aparecem preenchidos. Esta cena **não depende mais de slots disponíveis** — a disponibilidade não é capacidade dessa tela, e nenhum horário livre pode ser mostrado ou sugerido aqui.
- Risco: mostrar duração como campo próprio da interface, ou fazer aparecer botões de edição, remarcação ou exclusão que a tela não oferece; exibir nome, telefone ou e-mail reais.
- Status da cena: rascunho — pendente de execução autenticada

### Cena 6 — Ação de status comprovada

- Objetivo: mostrar uma única ação comprovada da agenda do gestor: confirmar manualmente um agendamento fictício.
- Duração estimada: pendente de edição
- Visual: um agendamento fictício recebe a ação Confirmar. Não mostrar conclusão, cancelamento, no-show, mensagens ou qualquer segunda transição.
- Texto na tela: "Atualizar o status do atendimento."
- Narração: "Quando a gestão confirma o atendimento, o status fica registrado na agenda."
- Evidência utilizada: ação de confirmação de status confirmada no código da agenda, entre as ações de status (confirmação, conclusão, registro de no-show e cancelamento) e o pagamento local; o cancelamento também é coberto por teste automatizado (seções 4 e 8 da validação funcional). Apenas a confirmação entra na demonstração.
- Validação necessária: efetivação da ação em navegador autenticado, em ambiente local com emuladores e dados fictícios, antes de gravar. Sem essa execução autenticada a cena não é demonstrável.
- Risco: a cena não pode sugerir confirmação automática, mensagem enviada ao cliente, notificação, reminder, segunda transição de status, edição ou remarcação. Confirmar aqui é ato manual da gestão registrado na tela, não um contato com o cliente.
- Status da cena: rascunho — pendente de execução autenticada

### Cena 7 — Chamada para ação

- Objetivo: convidar para conhecer a agenda do Marca Salão.
- Duração estimada: pendente de edição
- Visual: arte final com a identidade da marca e a chamada; sem simular botão clicável na imagem.
- Texto na tela: "Conheça a agenda do Marca Salão."
- Narração: "Conheça a agenda do Marca Salão."
- Evidência utilizada: CTA principal e destino documentados na seção 12 do briefing — [`https://marcasalao.com.br`](https://marcasalao.com.br).
- Validação necessária: confirmar por canal — no Instagram, orientar "link na bio" somente se o link externo do perfil estiver conferido na data da publicação; no Facebook, usar a URL completa na legenda. Não prometer acesso ao painel de demonstração, que exige credenciais não armazenadas neste repositório. Rastreamento: pendente, sem mecanismo definido.
- Risco: insinuar que clicar na imagem abre o site; prometer acesso direto ao painel; sugerir automação de mensagens, preenchimento da agenda, prevenção de faltas, agenda sempre cheia ou resultado financeiro.
- Status da cena: rascunho

## 7. Texto corrido de narração

Bloco contínuo para revisão; a narração é entregue como texto separado, sem gerar áudio neste repositório.

> Você consegue visualizar os agendamentos do seu salão com clareza?
>
> Quando uma parte da agenda fica no caderno, outra na conversa e outra na planilha, reunir as informações pode tomar tempo no meio do atendimento.
>
> Na agenda do painel, o registro é o mesmo: dá para olhar o dia, a semana ou o mês.
>
> Dá para filtrar por profissional, por status, ou buscar o nome de um cliente.
>
> Abrindo o atendimento, aparecem o horário, o cliente, o profissional, o serviço, o preço e o status.
>
> Quando a gestão confirma o atendimento, o status fica registrado na agenda.
>
> Conheça a agenda do Marca Salão.

Nenhuma linha deste bloco menciona lembrete, scheduler, notificação ou provedor de mensagem.

## 8. Textos na tela

Ordem das cenas:

1. "Você consegue visualizar os agendamentos do seu salão com clareza?"
2. "Quando as informações ficam espalhadas, cada lugar mostra um pedaço do dia."
3. "O mesmo registro, visto por dia, semana ou mês."
4. "Filtrar por profissional, por status, ou buscar pelo nome."
5. "Abrir um atendimento e ver os dados dele."
6. "Atualizar o status do atendimento."
7. "Conheça a agenda do Marca Salão."

Regras aplicadas: frases curtas, legíveis em tela vertical 1080x1920, sem estatística, sem valor financeiro, sem referência a horários disponíveis e sem afirmação maior do que a evidência disponível.

## 9. Plano de demonstração

### Confirmado no código

Sustentado pela leitura do commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee` (branch `codex/release-evidence`). Nada desta lista foi aberto em navegador:

- visões dia, semana e mês;
- agendamentos ocupados;
- filtros por profissional e status;
- busca por cliente;
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
- exportação CSV;
- estado vazio;
- estado de erro;
- estrutura responsiva no código.

Elementos também visíveis na captura consultada, [../../../01-insta-stories/05_agenda.png](../../../01-insta-stories/05_agenda.png) (registrada no Git em 02/10/2026 pelo commit `a6e7f79`): cabeçalho "AGENDA DO SALÃO", subtítulo "Acompanhe os atendimentos por período, profissional e status.", controles de data, seletor Dia/Semana/Mês, campo "Buscar cliente", seletores "Todos os profissionais" e "Todos status", grade com marcador "08:00", controle "Exportar CSV" e o item de menu "Agendamentos". Uma captura prova apenas o que está visível nela.

### Confirmado por testes automatizados selecionados

Comportamentos isolados executados durante a validação, com mocks ou em jsdom. Não equivalem a executar a aplicação:

- alternância entre as visões semana e mês, sustentada pelo teste correspondente;
- regras isoladas de agendamento na biblioteca do fluxo público (criação, pagamento pendente, conclusão, espera de pagamento);
- cancelamento e recusa entre tenants;
- regras isoladas do lembrete de 24 horas, com envio mockado.

Sobre o último item, registrar a formulação técnica vigente: O Salao02 contém implementação técnica de notificações e lembrete de 24 horas, mas implantação, configuração dos canais e entrega real não foram validadas para esta campanha. A NS-001 não está autorizada a prometer ou demonstrar essas capacidades. **Não apresentar testes de reminder como autorização promocional**, e não citar reminder, scheduler ou provedores em texto de tela ou narração.

### Pendente de execução autenticada

Nenhum item abaixo foi observado em tela; todos precisam de execução local com emuladores e dados fictícios antes de qualquer gravação:

- renderização real da agenda;
- login e autorização;
- carregamento dos dados;
- filtros no navegador;
- busca no navegador;
- abertura do modal;
- ações de status;
- integração real com Firestore;
- comportamento móvel;
- captura atualizada;
- uso de dados fictícios;
- experiência completa no Chromium.

### Proibido demonstrar ou afirmar na NS-001

- slots disponíveis na agenda do gestor;
- criação;
- edição;
- remarcação;
- exclusão;
- duração como campo próprio;
- preenchimento automático;
- prevenção automática de no-show;
- mensagens automáticas como promessa;
- reminder como promessa;
- confirmação automática;
- ocupação garantida;
- faturamento garantido.

Nada dessa lista pode aparecer de forma implícita: nenhuma cena, texto de tela ou narração deve sugerir que a agenda avisa, oferece, reserva, completa ou cobra algo.

## 10. Materiais necessários

- Execução autenticada da agenda em ambiente local com emuladores e dados fictícios, registrada com responsável e data.
- Captura atual da agenda, obtida nessa execução; a única registrada no repositório é de 02/10/2026 e não prova o estado atual da tela.
- Validação de resolução e legibilidade da captura no formato vertical.
- Gravação de tela somente após validar o fluxo escolhido. O acesso ao ambiente de execução é obtido junto ao responsável pelo projeto — credenciais não ficam neste repositório, e a antiga conta demo não pode ser usada.
- Elementos oficiais de marca existentes em [`../../../marcas/marcasalao/posts/`](../../../marcas/marcasalao/posts/): identidade verde-petróleo, menta e branco, logo MS/tesoura.
- Fundo e enquadramento visual das cenas sem produto.
- Texto de narração separado por cenas e tempos, entregue em `04-legendas/` (etapa própria, não criada aqui).
- Legendas visíveis sincronizadas e `.srt` correspondente (etapa própria).
- Arte final com CTA específico por canal.
- Revisão de dados pessoais em cada captura e quadro.
- Fonte identificável para qualquer dado que venha a ser usado; sem fonte, o dado não entra na peça.

## 11. Proteção de dados

- Não usar dados reais de clientes em nenhuma cena.
- Ocultar nomes, telefones, e-mails e observações de atendimento.
- Não exibir credenciais, sessões ou dados de acesso ao painel.
- Não abrir console ou ferramentas de desenvolvimento durante a gravação.
- Usar somente dados fictícios criados no ambiente local de emuladores; o ambiente "Studio Bella – Demonstração" aparece na captura histórica e não substitui a revalidação.
- Não usar a antiga conta demo.
- Não exportar CSV em ambiente real.
- Revisar cada quadro antes de aprovar o material.

## 12. Pendências

- Executar o E2E local com emuladores (runbook `docs/runbooks/local-full-user-journey-e2e.md` do repositório `Jonatasbottaro/Salao02`) e registrar responsável e data.
- Confirmar em navegador as visões dia, semana e mês, os filtros, a busca, o modal e a ação de status demonstrada.
- Validar comportamento em celular e legibilidade em tela vertical.
- Refazer a captura da agenda a partir do ambiente validado.
- Confirmar o texto revisado do hook editorialmente, junto da revisão dos candidatos em `../../../02-hooks/campanhas/NS-001/hooks.md`.
- Confirmar o CTA e o destino por canal, inclusive o link externo do perfil antes de prometer "link na bio".
- Definir o responsável pela campanha e pela aprovação.
- Revisar os textos de tela e a narração.
- Validar a ausência de dados pessoais em cada quadro.
- Estimar a duração depois da leitura cronometrada.
- Aprovar o briefing antes de qualquer produção.

## 13. Checklist editorial

- [ ] O briefing está aprovado.
- [ ] O hook está aprovado.
- [ ] A funcionalidade demonstrada foi validada por execução autenticada.
- [ ] A captura está atualizada.
- [ ] A demonstração corresponde ao produto atual.
- [ ] O comportamento móvel foi validado.
- [ ] Nenhum dado pessoal aparece.
- [ ] O roteiro não promete mensagens automáticas.
- [ ] O roteiro não promete lembretes automáticos.
- [ ] O roteiro não promete redução de faltas.
- [ ] O roteiro não promete aumento de faturamento.
- [ ] O CTA foi validado.
- [ ] A narração foi revisada.
- [ ] Os textos de tela foram revisados.
- [ ] O E2E local com emuladores foi executado.
- [ ] A agenda foi validada em Chromium.
- [ ] Os filtros foram validados no navegador.
- [ ] A busca foi validada no navegador.
- [ ] O modal foi validado no navegador.
- [ ] As ações demonstradas foram validadas em ambiente local.
- [ ] Todos os dados usados são fictícios.
- [ ] Nenhuma cena sugere horários disponíveis na agenda do gestor.
- [ ] Nenhuma cena apresenta reminder como promessa comercial.
- [ ] O roteiro foi aprovado para gravação.
- [ ] O roteiro foi aprovado para publicação.

Nenhum item está marcado: o briefing continua em validação, o hook continua em rascunho e a agenda ainda não foi executada em ambiente autenticado. Gravação e publicação permanecem bloqueadas.

## 14. Aprovação

- Elaborado por: assistente de marketing do Marca Salão, a partir do briefing NS-001 e do hook NS-001-H15, sob solicitação do titular em 2026-11-02
- Revisado por: pendente
- Aprovado por: pendente
- Data da aprovação: pendente
- Autorizado para gravação: não
- Autorizado para publicação: não
- Observações: "Roteiro revisado com base na auditoria técnica. A produção permanece bloqueada até execução autenticada local com emuladores e dados fictícios." Este documento não autoriza gravar, publicar, agendar nem registrar métricas. Estados e critério de pronto em [`../../README.md`](../../README.md).
