# Roteiro 001 — Organização e visibilidade da agenda

- Campanha: NS-001
- Briefing: [../../../00-briefings/campanhas/NS-001/briefing.md](../../../00-briefings/campanhas/NS-001/briefing.md)
- Biblioteca de hooks: [../../../02-hooks/campanhas/NS-001/hooks.md](../../../02-hooks/campanhas/NS-001/hooks.md)
- Validação funcional: [../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md)
- Hook selecionado: NS-001-H15 (texto revisado)
- Status do briefing: em validação
- Status do hook: rascunho
- Status do roteiro: rascunho
- Versão: 0.3
- Aprovação: pendente
- Autorizado para gravação: não
- Autorizado para publicação: não
- Data de criação: 2026-11-02
- Data da revisão: 2026-11-05
- Responsável: pendente de definição, se não documentado
- Validação por execução autenticada: [../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md)

> **Este roteiro permanece como rascunho editorial. A gravação e a publicação não estão autorizadas. As cenas demonstrativas tiveram a execução autenticada concluída em 2026-11-05 (emuladores + Chromium, dados fictícios); o que falta agora é a aprovação editorial do titular.**

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
- **Validação ainda necessária:** execução autenticada da tela em ambiente local com emuladores e dados fictícios concluída em 2026-11-05 ([VALIDACAO-EXECUCAO-2026-11-05.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md)). Nada deste roteiro pode ser gravado antes da aprovação editorial do titular.

**Seleção anterior — histórico.** A versão 0.1 deste roteiro usava o hook NS-001-H01, com a pergunta sobre horários ainda disponíveis, como texto da Cena 1. A evidência técnica classificou a disponibilidade como capacidade não suportada pela agenda do gestor, então aquela formulação foi **descartada** deste documento e permanece registrada apenas em [`../../../02-hooks/campanhas/NS-001/hooks.md`](../../../02-hooks/campanhas/NS-001/hooks.md), como texto original e histórico. Não usar como mensagem atual, texto de tela ou narração.

## 4. Formato proposto

- Formato: vídeo vertical, proposto — não produzido.
- Proporção: 9:16, sustentada pela documentação existente do repositório (`01-insta-stories/README.md` trata os assets como 1080x1920; `WORKFLOW.md` manda salvar PNG 1080x1920 e exportar 1080x1920 a 30fps).
- Canais possíveis: Instagram Reels e Stories, YouTube Shorts, TikTok.
- Duração final: pendente de leitura e edição; nenhuma duração é afirmada aqui.
- Demonstração: execução autenticada em ambiente local com emuladores e dados fictícios concluída em 2026-11-05; gravação condicionada à aprovação editorial.
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
- Validação necessária: nenhuma para a pergunta em si; as cenas demonstrativas (3 a 6) tiveram a execução autenticada concluída em 2026-11-05.
- Risco: ser lido como garantia de que a tela revela algo que não foi registrado nela, ou como crítica à forma como o salão trabalha hoje.
- Status da cena: rascunho editorial

### Cena 2 — Situação de informação espalhada

- Objetivo: mostrar a rotina em que a informação do dia não está reunida em um só lugar, e o esforço operacional disso.
- Duração estimada: pendente de edição
- Visual: anotações, conversa e planilha em telas separadas, sem marca de produto.
- Texto na tela: "Quando as informações ficam espalhadas, cada lugar mostra um pedaço do dia."
- Narração: "Quando uma parte da agenda fica no caderno, outra na conversa e outra na planilha, reunir as informações pode tomar tempo no meio do atendimento."
- Evidência utilizada: dor e impacto operacional qualitativos das seções 4 e 5 do briefing 0.2.
- Validação necessária: nenhuma, pois a cena não mostra o produto; o registro em múltiplos lugares é situação do salão, não comportamento do sistema.
- Risco: a situação é **condicional** — o texto começa com "quando" e só vale para o salão em que ela de fato ocorre. Não há pesquisa que sustente apresentá-la como realidade de todos os salões ou da maior parte deles, e o roteiro não pode ser lido dessa forma. A cena também não pode servir para classificar o estabelecimento como desorganizado, nem afirmar prejuízo, perda de clientes ou redução de faturamento.
- Status da cena: rascunho editorial

### Cena 3 — Visões dia, semana e mês

- Objetivo: mostrar a mesma rotina em três granularidades de visualização.
- Duração estimada: pendente de edição
- Visual: seletor de visualização da agenda acionado entre "Dia", "Semana" e "Mês", com navegação de data; somente dados fictícios.
- Texto na tela: "O mesmo registro, visto por dia, semana ou mês."
- Narração: "Na agenda do painel, o registro é o mesmo: dá para olhar o dia, a semana ou o mês."
- Evidência utilizada: página da agenda do gestor, `AgendaViewSwitcher.tsx` e `CalendarGrid.tsx` no commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee`, registrados na seção 8 da validação funcional; controles também visíveis em [../../../01-insta-stories/05_agenda.png](../../../01-insta-stories/05_agenda.png).
- Validação necessária: comportamento confirmado no código e em teste automatizado selecionado (alternância entre semana e mês); visões Dia, Semana e Mês e navegação por data observadas em navegador autenticado em 2026-11-05, inclusive estado atual da tela e legibilidade em viewport móvel emulado (verificação em aparelho físico real permanece fora do escopo).
- Risco: apresentar a troca de visão como se já estivesse testada em uso real, ou sugerir que a agenda mostra o que não foi registrado nela.
- Status da cena: tecnicamente validada; pendente de aprovação editorial e produção

### Cena 4 — Filtros e busca

- Objetivo: mostrar como recortar a listagem por profissional, por status e pelo nome do cliente.
- Duração estimada: pendente de edição
- Visual: seletores "Todos os profissionais" e "Todos status" alterados e campo de busca por nome de cliente, com a listagem reagindo; somente dados fictícios.
- Texto na tela: "Filtrar por profissional, por status, ou buscar pelo nome."
- Narração: "Dá para filtrar por profissional, por status, ou buscar o nome de um cliente."
- Evidência utilizada: filtros por profissional e status e busca por cliente confirmados no código da agenda do gestor (seções 4 e 8 da validação funcional).
- Validação necessária: os valores de status observados foram Pendente, Confirmado, Concluído, Cancelado e No-show; filtro por profissional, filtro por status e busca por cliente foram executados em navegador autenticado na execução de 2026-11-05. Nenhuma busca por serviço ou por período foi prometida ou demonstrada. Não mostrar filtro inexistente nem busca por serviço ou por período que não esteja implementado.
- Risco: insinuar que a tela aponta disponibilidade, sugere horários ou encontra sozinha o que a pessoa procura; a consulta é feita pela pessoa.
- Status da cena: tecnicamente validada; pendente de aprovação editorial e produção

### Cena 5 — Detalhes de um agendamento fictício

- Objetivo: mostrar o que aparece ao abrir um agendamento na agenda do gestor.
- Duração estimada: pendente de edição
- Visual: modal de detalhes aberto sobre um agendamento fictício, exibindo horário, cliente fictício, profissional fictício, serviço fictício, preço fictício e status.
- Texto na tela: "Abrir um atendimento e ver os dados dele."
- Narração: "Abrindo o atendimento, aparecem o horário, o cliente, o profissional, o serviço, o preço e o status."
- Evidência utilizada: `BookingDetailModal.tsx` e os campos horário, cliente, profissional, serviço, preço e status registrados como confirmados no código (seções 4 e 8 da validação funcional).
- Validação necessária: modal aberto em navegador autenticado com dados fictícios na execução de 2026-11-05; os campos horário, cliente, profissional, serviço, preço, status e status de pagamento apareceram preenchidos. Esta cena **não depende mais de slots disponíveis** — a disponibilidade não é capacidade dessa tela, e nenhum horário livre pode ser mostrado ou sugerido aqui.
- Risco: mostrar duração como campo próprio da interface, ou fazer aparecer botões de edição, remarcação ou exclusão que a tela não oferece; exibir nome, telefone ou e-mail reais.
- Status da cena: tecnicamente validada; pendente de aprovação editorial e produção

### Cena 6 — Ação de status comprovada

- Objetivo: mostrar uma única ação comprovada da agenda do gestor: confirmar manualmente um agendamento fictício.
- Duração estimada: pendente de edição
- Visual: um agendamento fictício recebe a ação Confirmar. Não mostrar conclusão, cancelamento, no-show, mensagens ou qualquer segunda transição.
- Texto na tela: "Atualizar o status do atendimento."
- Narração: "Quando a gestão confirma o atendimento, o status fica registrado na agenda."
- Evidência utilizada: ação de confirmação de status confirmada no código da agenda, entre as ações de status (confirmação, conclusão, registro de no-show e cancelamento) e o pagamento local; o cancelamento também é coberto por teste automatizado (seções 4 e 8 da validação funcional). Apenas a confirmação entra na demonstração.
- Validação necessária: ação Confirmar executada manualmente em navegador autenticado, em ambiente local com emuladores e dados fictícios, na execução de 2026-11-05 (Pendente → Confirmado, com persistência após recarga). Nenhuma mensagem foi enviada, nenhuma notificação externa foi exercitada e nenhuma confirmação automática ocorreu. A cena é demonstrável após a aprovação editorial.
- Risco: a cena não pode sugerir confirmação automática, mensagem enviada ao cliente, notificação, reminder, segunda transição de status, edição ou remarcação. Confirmar aqui é ato manual da gestão registrado na tela, não um contato com o cliente.
- Status da cena: tecnicamente validada; pendente de aprovação editorial e produção

### Cena 7 — Chamada para ação

- Objetivo: convidar para conhecer a agenda do Marca Salão.
- Duração estimada: pendente de edição
- Visual: arte final com a identidade da marca e a chamada; sem simular botão clicável na imagem.
- Texto na tela: "Conheça a agenda do Marca Salão."
- Narração: "Conheça a agenda do Marca Salão."
- Evidência utilizada: CTA principal e destino documentados na seção 12 do briefing — [`https://marcasalao.com.br`](https://marcasalao.com.br).
- Validação necessária: confirmar por canal — no Instagram, orientar "link na bio" somente se o link externo do perfil estiver conferido na data da publicação; no Facebook, usar a URL completa na legenda. Não prometer acesso ao painel de demonstração, que exige credenciais não armazenadas neste repositório. Rastreamento: pendente, sem mecanismo definido.
- Risco: insinuar que clicar na imagem abre o site; prometer acesso direto ao painel; sugerir automação de mensagens, preenchimento da agenda, prevenção de faltas, agenda sempre cheia ou resultado financeiro.
- Status da cena: rascunho editorial

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

Sustentado pela leitura do commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee` (branch `codex/release-evidence`). Na auditoria técnica inicial, essas capacidades foram confirmadas por leitura de código; a execução autenticada posterior está registrada em [`VALIDACAO-EXECUCAO-2026-11-05.md`](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md):

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

### Execução autenticada — concluída em 2026-11-05

Os itens abaixo foram observados em tela na execução autenticada de 2026-11-05 ([VALIDACAO-EXECUCAO-2026-11-05.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md)), em Chromium com emuladores e dados fictícios:

- renderização real da agenda;
- login e autorização;
- carregamento dos dados;
- filtros no navegador;
- busca no navegador;
- abertura do modal;
- ações de status;
- captura atualizada;
- uso de dados fictícios;
- experiência no Chromium, inclusive viewport mobile 390×844.

Permanecem fora do escopo desta validação, por definição: integração com Firestore de produção (a validação é local com emuladores) e teste em aparelho físico real (a verificação mobile foi por emulação de viewport).

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

- Execução autenticada da agenda em ambiente local com emuladores e dados fictícios: concluída em 2026-11-05, registrada com responsável e data em [VALIDACAO-EXECUCAO-2026-11-05.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md).
- Captura atual da agenda obtida nessa execução, em [capturas/2026-11-05/](../../../00-briefings/campanhas/NS-001/capturas/2026-11-05/); a captura de 02/10/2026 permanece apenas como histórico.
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

Resolvidas em 2026-11-05 pela execução autenticada ([VALIDACAO-EXECUCAO-2026-11-05.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md)): E2E local com emuladores executado e registrado com responsável e data; visões dia, semana e mês, filtros, busca, modal e ação de status confirmados em navegador; legibilidade em viewport mobile validada; captura da agenda refeita a partir do ambiente validado; ausência de dados pessoais conferida nas capturas de evidência.

Continuam abertas:

- Confirmar o texto revisado do hook editorialmente, junto da revisão dos candidatos em `../../../02-hooks/campanhas/NS-001/hooks.md`.
- Confirmar o CTA e o destino por canal, inclusive o link externo do perfil antes de prometer "link na bio".
- Definir o responsável pela campanha e pela aprovação.
- Revisar os textos de tela e a narração.
- Validar a ausência de dados pessoais em cada quadro da gravação final (as capturas de evidência já foram conferidas; a gravação ainda não existe).
- Estimar a duração depois da leitura cronometrada.
- Aprovar o briefing antes de qualquer produção.
- Confirmar qual nome e identidade visual são oficiais para uso público antes da produção final (a interface capturada exibe "Meu Salão"; a campanha usa "Marca Salão"); não alterar o produto nem editar capturas sem autorização.

## 13. Checklist editorial

- [ ] O briefing está aprovado.
- [ ] O hook está aprovado.
- [x] A funcionalidade demonstrada foi validada por execução autenticada.
- [x] A captura de evidência está atualizada.
- [ ] A demonstração final corresponde ao produto atual.
- [x] O comportamento móvel foi validado em viewport emulado.
- [x] Nenhum dado pessoal aparece nas capturas de evidência.
- [x] O roteiro não promete mensagens automáticas.
- [x] O roteiro não promete lembretes automáticos.
- [x] O roteiro não promete redução de faltas.
- [x] O roteiro não promete aumento de faturamento.
- [ ] O CTA por canal foi validado.
- [ ] A narração foi revisada e aprovada.
- [ ] Os textos de tela foram revisados e aprovados.
- [x] O E2E local com emuladores foi executado.
- [x] A agenda foi validada em Chromium.
- [x] Os filtros foram validados no navegador.
- [x] A busca foi validada no navegador.
- [x] O modal foi validado no navegador.
- [x] A ação Confirmar foi validada no ambiente local.
- [x] Todos os dados das evidências são fictícios.
- [x] Nenhuma cena sugere horários disponíveis na agenda do gestor.
- [x] Nenhuma cena apresenta reminder como promessa comercial.
- [ ] A gravação final foi revisada para dados pessoais.
- [ ] O roteiro foi aprovado para gravação.
- [ ] O roteiro foi aprovado para publicação.

Itens marcados por evidência: a execução autenticada de 2026-11-05 ([VALIDACAO-EXECUCAO-2026-11-05.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md)) cobre validação em Chromium, filtros, busca, modal, ação Confirmar, comportamento móvel em viewport emulado, captura de evidência atualizada e dados fictícios; os itens de promessa refletem o texto atual do roteiro. "A demonstração final corresponde ao produto atual" e "A gravação final foi revisada para dados pessoais" permanecem abertos porque nenhuma peça foi gravada. Aprovações de briefing, hook, CTA, textos, gravação e publicação continuam com o titular: gravação e publicação permanecem bloqueadas.

As capturas de 2026-11-05 são evidência técnica. Não estão automaticamente aprovadas como frames de publicação: trazem identificação técnica E2E, enquadramento de validação, possíveis valores fictícios inadequados e ainda exigem adaptação vertical, revisão de marca, fixture editorial dedicada e revisão quadro a quadro.

## 14. Aprovação

- Elaborado por: assistente de marketing do Marca Salão, a partir do briefing NS-001 e do hook NS-001-H15, sob solicitação do titular em 2026-11-02
- Revisado por: pendente
- Aprovado por: pendente
- Data da aprovação: pendente
- Autorizado para gravação: não
- Autorizado para publicação: não
- Observações: "Roteiro revisado com base na auditoria técnica. A execução autenticada local com emuladores e dados fictícios foi concluída em 2026-11-05; a produção permanece bloqueada até a aprovação editorial do briefing, do hook e deste roteiro pelo titular." Este documento não autoriza gravar, publicar, agendar nem registrar métricas. Estados e critério de pronto em [`../../README.md`](../../README.md).
