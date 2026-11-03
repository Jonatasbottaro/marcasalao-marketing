# Hooks da campanha NS-001

- Campanha: NS-001
- Briefing: [../../../00-briefings/campanhas/NS-001/briefing.md](../../../00-briefings/campanhas/NS-001/briefing.md)
- Validação funcional: [../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md)
- Status do briefing: em validação
- Status desta biblioteca: rascunho
- Versão: 0.2
- Aprovação: pendente
- Uso em produção: não autorizado

> **Estes hooks são rascunhos editoriais. A validação técnica da agenda existe e está registrada (leitura de código e testes selecionados do commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee`), mas a execução autenticada em ambiente local com emuladores ainda não foi feita. Nenhum hook deste documento está aprovado para publicação ou produção.**

Contexto de produto que vale para todos os hooks abaixo, revisado pela validação técnica:

- **Agenda do gestor** (`/gestor/agenda`): tela de **visualização e acompanhamento** dos agendamentos — visões dia, semana e mês, filtros por profissional e status, busca por nome do cliente, modal de detalhes e ações de status. Confirmado no código.
- **Não suportado pela agenda do gestor**: exibir slots livres, oferecer horários disponíveis, criar, editar, remarcar, excluir agendamento, mostrar duração como campo próprio ou preencher a agenda automaticamente.
- **Superfície correta para disponibilidade e criação**: o fluxo público do cliente (`/api/public/availability` e o wizard de agendamento). Hook sobre "horário livre" pertence a essa superfície, não à tela do gestor.
- **Contato com o cliente**: O Salao02 contém implementação técnica de notificações e lembrete de 24 horas, mas implantação, configuração dos canais e entrega real não foram validadas para esta campanha. A NS-001 não está autorizada a prometer ou demonstrar essas capacidades. Continua proibido usar mensagem, lembrete ou confirmação automática como argumento de hook.
- **Desempenho**: nenhum hook foi publicado ou medido; nenhuma previsão de conversão, viralização ou desempenho é feita neste documento.

---

## Categoria: pergunta

### NS-001-H01

- **ID:** NS-001-H01
- **Categoria:** pergunta
- **Texto:** "Você sabe quais horários ainda estão disponíveis no seu salão?" — **texto original, preservado como histórico; descartado para o roteiro 001; não usar como mensagem atual**
- **Público pretendido:** pessoas responsáveis pela gestão de salões de beleza que organizam a própria agenda.
- **Dor abordada:** falta de clareza sobre a ocupação da agenda e sobre os espaços livres do dia.
- **Continuação sugerida:** mostrar a tela da agenda e percorrer a grade do dia, apontando onde os atendimentos aparecem.
- **Evidência necessária:** validação funcional de que a agenda do Marca Salão exibe os horários disponíveis de forma legível. A captura `01-insta-stories/05_agenda.png` mostra a grade de um dia, mas não comprova por si só esse comportamento.
- **Risco de interpretação:** ser lido como se o sistema avisasse ou apontasse sozinho os buracos da agenda.
- **Status:** rascunho — descartado para o roteiro 001 (ver "Revisão pela validação técnica" abaixo)
- **Observações:** era a formulação registrada como permitida no briefing NS-001 versão 0.1, seção 4; o briefing 0.2 a substituiu pela pergunta sobre clareza dos agendamentos.

**Revisão pela validação técnica (v0.2)**

- **Resultado da validação técnica:** a exibição de horários disponíveis e de slots livres foi verificada como **ausente** na agenda autenticada do gestor; disponibilidade e criação existem no fluxo público do cliente. Seções 4, 5 e 9 de [VALIDACAO-FUNCIONAL-AGENDA.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md).
- **Classificação editorial:** descartado para o roteiro 001.
- **Texto original:** "Você sabe quais horários ainda estão disponíveis no seu salão?" (mantido, não apagado).
- **Texto revisado proposto:** nenhum — a formulação inteira depende da capacidade ausente. A pergunta que ocupa seu lugar no roteiro 001 é a do hook NS-001-H15 revisado.
- **Motivo da revisão:** manter este texto como mensagem atual atribuiria à tela do gestor uma capacidade que o código localizou em outra superfície.
- **Superfície correta do produto:** fluxo público do cliente (consulta de disponibilidade pelo cliente), não a agenda do gestor.
- **Status após validação:** descartado para o roteiro 001; continua **rascunho** como registro histórico da biblioteca, sem aprovação.
- **Decisão anterior preservada:** este hook foi o selecionado para o roteiro 001 em 2026-11-02 (versão 0.1 desta biblioteca). A seleção foi revisada por evidência técnica e substituída; o histórico da escolha permanece registrado aqui e na seção de seleção editorial.

### NS-001-H02

- **ID:** NS-001-H02
- **Categoria:** pergunta
- **Texto:** "Se um cliente ligar agora pedindo um horário, você consegue responder na hora qual espaço está livre?"
- **Público pretendido:** quem atende telefone ou mensagens no salão e precisa responder sem hesitar.
- **Dor abordada:** dificuldade de responder rapidamente sobre disponibilidade durante o atendimento.
- **Continuação sugerida:** encenar a consulta à agenda no computador ou no celular do salão e mostrar o que aparece na tela.
- **Evidência necessária:** validação de que a consulta a um dia específico é feita na tela de agenda e de como ela se comporta em celular.
- **Risco de interpretação:** sugerir que o sistema responde ao cliente ou faz isso automaticamente.
- **Status:** rascunho
- **Observações:** a resposta continua sendo dada pela pessoa, não pelo sistema; deixar isso claro no roteiro.

**Revisão pela validação técnica (v0.2)**

- **Resultado da validação técnica:** responder "qual espaço está livre" exige cálculo de disponibilidade, confirmado apenas no fluxo público do cliente; a agenda do gestor mostra os agendamentos existentes, não as lacunas. Seções 4, 5 e 9 da validação.
- **Classificação editorial:** requer reenquadramento para o fluxo público.
- **Texto original:** "Se um cliente ligar agora pedindo um horário, você consegue responder na hora qual espaço está livre?" (mantido, não apagado).
- **Texto revisado proposto:** "Se um cliente ligar agora, você consegue abrir a agenda e ver o que já está marcado?"
- **Motivo da revisão:** desloca a promessa de "saber o espaço livre" para a capacidade comprovada da tela do gestor — visualizar e acompanhar os agendamentos registrados.
- **Superfície correta do produto:** a disponibilidade em si pertence ao fluxo público do cliente; a agenda do gestor pertence à consulta dos agendamentos.
- **Status após validação:** requer reenquadramento para o fluxo público; **rascunho**, não selecionado para o roteiro 001, sem aprovação.

### NS-001-H03

- **ID:** NS-001-H03
- **Categoria:** pergunta
- **Texto:** "Quantos lugares diferentes você consulta para saber como está a semana do salão?"
- **Público pretendido:** gestores que acompanham a agenda em mais de uma fonte.
- **Dor abordada:** agenda fragmentada entre caderno, planilha e conversas.
- **Continuação sugerida:** reconhecer as fontes espalhadas e, em seguida, mostrar os atendimentos registrados em uma única tela do sistema.
- **Evidência necessária:** validação de que a agenda centraliza os agendamentos registrados no sistema e de quais visualizações (dia, semana, mês) existem de fato.
- **Risco de interpretação:** afirmar que o sistema importa ou sincroniza dados que hoje estão em caderno ou planilha.
- **Status:** rascunho
- **Observações:** a pergunta não afirma que o salão usa vários lugares; convide a pessoa a conferir a própria rotina.

---

## Categoria: dor

### NS-001-H04

- **ID:** NS-001-H04
- **Categoria:** dor
- **Texto:** "No meio da correria do dia, é fácil perder de vista quantos atendimentos ainda faltam."
- **Público pretendido:** quem acompanha vários atendimentos ao mesmo tempo no salão.
- **Dor abordada:** dificuldade de acompanhar vários atendimentos em andamento ao longo do dia.
- **Continuação sugerida:** abrir a agenda do dia e percorrer os registros, mostrando como eles aparecem organizados por horário.
- **Evidência necessária:** validação de que a tela do dia lista os atendimentos agendados e permite acompanhá-los.
- **Risco de interpretação:** transformar a frase em afirmação financeira ("isso está te fazendo perder dinheiro") — proibido sem evidência.
- **Status:** rascunho
- **Observações:** fala de atenção e rotina, não de prejuízo.

### NS-001-H05

- **ID:** NS-001-H05
- **Categoria:** dor
- **Texto:** "Uma parte da agenda fica no caderno, outra no celular e outra na memória. Nenhuma delas mostra o dia inteiro."
- **Público pretendido:** salões que registram agendamentos em fontes separadas.
- **Dor abordada:** agenda fragmentada, sem uma visão única do dia.
- **Continuação sugerida:** comparar as fontes espalhadas com a tela de agenda do sistema, mostrando apenas o que aparece nela.
- **Evidência necessária:** validação de que a agenda exibe uma visão completa do dia para os registros feitos no próprio sistema.
- **Risco de interpretação:** soar como crítica ao uso de caderno, ou insinuar que o sistema puxa os dados que estão fora dele.
- **Status:** rascunho
- **Observações:** descrever a situação sem ridicularizar o método atual do salão.

### NS-001-H06

- **ID:** NS-001-H06
- **Categoria:** dor
- **Texto:** "Dá para saber que o dia está cheio — mas nem sempre fica claro onde ainda existe espaço."
- **Público pretendido:** gestores que sentem a agenda apertada sem conseguir localizar as lacunas.
- **Dor abordada:** falta de clareza sobre a distribuição dos horários dentro do dia.
- **Continuação sugerida:** mostrar a grade de um dia e apontar, na tela, os intervalos sem atendimento registrado.
- **Evidência necessária:** validação de que a grade deixa legíveis os intervalos livres entre atendimentos.
- **Risco de interpretação:** levar à expectativa de que o sistema identifica e oferece esses espaços automaticamente.
- **Status:** rascunho
- **Observações:** a identificação continua sendo feita pela pessoa que olha a tela.

**Revisão pela validação técnica (v0.2)**

- **Resultado da validação técnica:** "onde ainda existe espaço" depende da exibição de slots livres, classificada como **não suportada** na agenda do gestor. A grade mostra os atendimentos registrados; não há componente alcançado que calcule lacunas na tela autenticada.
- **Classificação editorial:** não suportado pela agenda do gestor.
- **Texto original:** "Dá para saber que o dia está cheio — mas nem sempre fica claro onde ainda existe espaço." (mantido, não apagado).
- **Texto revisado proposto:** "Dá para saber que o dia está cheio — mas nem sempre é fácil ver como os atendimentos se distribuíram."
- **Motivo da revisão:** mantém a observação sobre leitura do dia e remove a promessa de localizar espaços, que a tela do gestor não entrega.
- **Superfície correta do produto:** cálculo de espaços livres = fluxo público do cliente; distribuição dos atendimentos já registrados = agenda do gestor.
- **Status após validação:** não suportado pela agenda do gestor na formulação original; versão revisada segue como **rascunho**, sem seleção para o roteiro 001.

---

## Categoria: diagnóstico

### NS-001-H07

- **ID:** NS-001-H07
- **Categoria:** diagnóstico
- **Texto:** "Se responder 'tem horário livre agora?' exige parar tudo e procurar, talvez valha olhar como o registro está sendo feito."
- **Público pretendido:** responsáveis pela recepção e pela agenda do salão.
- **Dor abordada:** esforço para responder rapidamente sobre disponibilidade.
- **Continuação sugerida:** convidar a acompanhar uma consulta real na agenda, do começo ao fim.
- **Evidência necessária:** nenhuma para a pergunta em si; a demonstração que a segue depende da validação da consulta na agenda.
- **Risco de interpretação:** soar como diagnóstico de desorganização do estabelecimento.
- **Status:** rascunho
- **Observações:** mantida a formulação condicional ("se... talvez valha"), sem afirmar que o salão é desorganizado.

**Revisão pela validação técnica (v0.2)**

- **Resultado da validação técnica:** a pergunta "tem horário livre agora?" é de disponibilidade — capacidade confirmada no fluxo público do cliente e **não suportada** na agenda do gestor. O esforço de parar e procurar, que é o núcleo do hook, permanece válido como dor de acompanhamento.
- **Classificação editorial:** requer reenquadramento para o fluxo público.
- **Texto original:** "Se responder 'tem horário livre agora?' exige parar tudo e procurar, talvez valha olhar como o registro está sendo feito." (mantido, não apagado).
- **Texto revisado proposto:** "Se responder sobre o dia exige parar tudo e procurar, talvez valha olhar como o registro está sendo feito."
- **Motivo da revisão:** troca o objeto da consulta (horário livre → informação do dia), mantendo a formulação condicional e o foco no esforço de procurar.
- **Superfície correta do produto:** se a intenção for o horário livre em si, a superfície é o agendamento público do cliente; a agenda do gestor cobre o que já está registrado.
- **Status após validação:** requer reenquadramento para o fluxo público; **rascunho**, não selecionado para o roteiro 001, sem aprovação.

### NS-001-H08

- **ID:** NS-001-H08
- **Categoria:** diagnóstico
- **Texto:** "Quando a informação do dia está em mais de um lugar, a agenda passa a depender de quem anotou."
- **Público pretendido:** donos e gerentes que dividem a gestão da agenda com a equipe.
- **Dor abordada:** dependência de pessoas específicas porque o registro não está concentrado.
- **Continuação sugerida:** mostrar como um agendamento registrado no sistema aparece para quem abre a agenda.
- **Evidência necessária:** validação de permissão e de visualização — quem consegue abrir a agenda e o que ela mostra.
- **Risco de interpretação:** prometer controle de acesso, sincronização ou multiusuário sem verificação.
- **Status:** rascunho
- **Observações:** não afirmar que vários usuários acessam a mesma agenda sem testar isso.

### NS-001-H09

- **ID:** NS-001-H09
- **Categoria:** diagnóstico
- **Texto:** "Quando a agenda fica difícil de ler, o plano do dia acaba sendo reconstruído de memória."
- **Público pretendido:** quem planeja a rotina do salão ao começar o expediente.
- **Dor abordada:** falta de uma visão centralizada e legível dos atendimentos.
- **Continuação sugerida:** acompanhar o começo de um dia de trabalho usando a tela de agenda como referência.
- **Evidência necessária:** validação de que a tela de agenda é legível o bastante para planejar o dia, inclusive em celular.
- **Risco de interpretação:** apresentar "visão centralizada" como fato já comprovado do produto.
- **Status:** rascunho
- **Observações:** marcar no roteiro que a centralização depende de validação funcional.

---

## Categoria: contraste

### NS-001-H10

- **ID:** NS-001-H10
- **Categoria:** contraste
- **Texto:** "Anotado em vários lugares, o dia aparece em pedaços. Registrado em um só, o dia aparece inteiro."
- **Público pretendido:** gestores comparando formas de organizar a agenda.
- **Dor abordada:** fragmentação da informação da agenda.
- **Continuação sugerida:** mostrar a grade de um dia completo na tela da agenda.
- **Evidência necessária:** validação de que a agenda registra e exibe os atendimentos do dia em uma única visão.
- **Risco de interpretação:** ler como "um lugar certo e outro errado"; o contraste é entre processos, não entre pessoas.
- **Status:** rascunho
- **Observações:** evitar qualquer formulação profissional versus amador.

### NS-001-H11

- **ID:** NS-001-H11
- **Categoria:** contraste
- **Texto:** "Procurar horário disponível é reconstruir a rotina. Consultar a agenda é abrir a tela e olhar o dia."
- **Público pretendido:** quem hoje verifica disponibilidade somando informações de origem diversa.
- **Dor abordada:** esforço da consulta manual contra a consulta organizada.
- **Continuação sugerida:** alternar na edição as duas situações — a busca manual e a tela da agenda — sem mencionar automação.
- **Evidência necessária:** validação de que a consulta na tela da agenda é viável na prática, inclusive a velocidade real do fluxo.
- **Risco de interpretação:** insinuar que o sistema encontra os horários sozinho ou que a consulta é imediata.
- **Status:** rascunho
- **Observações:** se a demonstração for gravada, registrar que ela mostra uma consulta feita pela pessoa.

**Revisão pela validação técnica (v0.2)**

- **Resultado da validação técnica:** "procurar horário disponível" não é tarefa da agenda do gestor; a tela confirma agendamentos registrados, visões dia/semana/mês, filtros e busca. O contraste entre reconstruir e consultar continua sustentado pelo código.
- **Classificação editorial:** não suportado pela agenda do gestor (no trecho de disponibilidade).
- **Texto original:** "Procurar horário disponível é reconstruir a rotina. Consultar a agenda é abrir a tela e olhar o dia." (mantido, não apagado).
- **Texto revisado proposto:** "Reconstruir a rotina de memória é procurar. Consultar a agenda é abrir a tela e olhar o dia."
- **Motivo da revisão:** preserva o contraste entre dois processos, trocando o objeto da busca de "horário disponível" para a rotina registrada, que é o que a tela entrega.
- **Superfície correta do produto:** disponibilidade = fluxo público do cliente; consulta do dia registrado = agenda do gestor.
- **Status após validação:** não suportado pela agenda do gestor na formulação original; versão revisada segue como **rascunho**, sem seleção para o roteiro 001.

### NS-001-H12

- **ID:** NS-001-H12
- **Categoria:** contraste
- **Texto:** "Antes: 'acho que cabe um atendimento no fim da tarde'. Depois de registrar tudo na agenda: 'vou ver o que aparece nesse horário'."
- **Público pretendido:** recepcionistas e donos que confirmam horários por suposição.
- **Dor abordada:** incerteza sobre a ocupação de um horário específico.
- **Continuação sugerida:** mostrar a consulta a um horário na grade da agenda.
- **Evidência necessária:** validação de que um horário individual pode ser localizado na visualização do dia.
- **Risco de interpretação:** sugerir prevenção automática de conflito de horário, o que ainda não está comprovado.
- **Status:** rascunho
- **Observações:** manter as aspas como fala, sem transformar em promessa de precisão do sistema.

**Revisão pela validação técnica (v0.2)**

- **Resultado da validação técnica:** "acho que cabe um atendimento" e "ver o que aparece nesse horário" pressupõem cálculo de cabimento e checagem de lacuna, capacidades confirmadas só no fluxo público do cliente; a agenda do gestor não foi implementada para sinalizar vagas, e a prevenção de conflito de horário não foi comprovada nessa tela.
- **Classificação editorial:** não suportado pela agenda do gestor (no trecho de disponibilidade).
- **Texto original:** "Antes: 'acho que cabe um atendimento no fim da tarde'. Depois de registrar tudo na agenda: 'vou ver o que aparece nesse horário'." (mantido, não apagado).
- **Texto revisado proposto:** "Antes: 'acho que atendi alguém nesse horário'. Depois de registrar tudo na agenda: 'vou ver o que está marcado nesse horário'."
- **Motivo da revisão:** move a fala de "caber um atendimento novo" para "conferir o que já está registrado", que é a ação comprovada na tela.
- **Superfície correta do produto:** checar se um horário comporta um atendimento = fluxo público; ver o que está marcado = agenda do gestor.
- **Status após validação:** não suportado pela agenda do gestor na formulação original; versão revisada segue como **rascunho**, sem seleção para o roteiro 001.

---

## Categoria: curiosidade

### NS-001-H13

- **ID:** NS-001-H13
- **Categoria:** curiosidade
- **Texto:** "O que dá para observar numa agenda do dia quando ela está toda preenchida no mesmo lugar?"
- **Público pretendido:** gestores que nunca viram a própria rotina reunida em uma tela.
- **Dor abordada:** falta de hábito de olhar a agenda como um todo.
- **Continuação sugerida:** percorrer a tela da agenda apontando um elemento visível por vez.
- **Evidência necessária:** relação dos elementos realmente presentes e funcionais na tela, conferida por validação e não apenas pela captura.
- **Risco de interpretação:** citar filtros, status ou visualizações que ainda não foram testados.
- **Status:** rascunho
- **Observações:** o roteiro deve mostrar só o que foi confirmado na tela.

### NS-001-H14

- **ID:** NS-001-H14
- **Categoria:** curiosidade
- **Texto:** "Existem detalhes na tela da agenda que mostram, sem esforço, como o dia se distribuiu."
- **Público pretendido:** quem abre a agenda rapidamente entre um atendimento e outro.
- **Dor abordada:** leitura pouco proveitosa de uma agenda cheia de registros.
- **Continuação sugerida:** mostrar onde olhar primeiro e o que cada parte da tela representa.
- **Evidência necessária:** validação de que os elementos citados existem e são legíveis na versão atual do sistema.
- **Risco de interpretação:** escorregar para linguagem de segredo ou truque, proibida pelo padrão editorial.
- **Status:** rascunho
- **Observações:** manter tom informativo; sem "ninguém te conta" e sem "método garantido".

### NS-001-H15

- **ID:** NS-001-H15
- **Categoria:** curiosidade
- **Texto:** "Quais informações, na agenda, ajudam a acompanhar os atendimentos sem reconstruir o dia de memória?"
- **Público pretendido:** responsáveis pela rotina diária do salão.
- **Dor abordada:** esforço mental para lembrar o que já foi agendado.
- **Continuação sugerida:** listar na prática, na tela, os campos que sustentam essa leitura e encerrar convidando para uma demonstração.
- **Evidência necessária:** validação de que os campos exibidos na agenda (cliente, serviço, profissional, horário) aparecem como esperado.
- **Risco de interpretação:** prometer mais clareza como resultado garantido do uso do sistema.
- **Status:** rascunho
- **Observações:** o gancho funciona como convite à demonstração, alinhado ao CTA do briefing.

**Revisão pela validação técnica (v0.2)**

- **Resultado da validação técnica:** os campos que sustentam a leitura do hook — horário, cliente, profissional, serviço, preço no modal e status — estão entre as capacidades confirmadas no código da agenda do gestor (validação, seção 4). O hook não depende de disponibilidade.
- **Classificação editorial:** mantém-se elegível; nenhum dos três rótulos de descarte se aplica.
- **Texto original:** "Quais informações, na agenda, ajudam a acompanhar os atendimentos sem reconstruir o dia de memória?" (mantido, não apagado).
- **Texto revisado proposto:** "Você consegue visualizar os agendamentos do seu salão com clareza?"
- **Motivo da revisão:** encurta a frase para tela vertical, alinha o vocabulário ao do briefing v0.2 ("visualizar", "agendamentos", "clareza") e conserva o sentido do original — ler o dia sem reconstruí-lo de memória.
- **Superfície correta do produto:** agenda do gestor (visualização e acompanhamento).
- **Status após validação:** selecionado para o roteiro 001; **rascunho**, sem aprovação, sem autorização de produção.

---

## Triagem para a próxima etapa

| ID | Categoria | Resultado da validação técnica | Classificação editorial | Status |
| --- | --- | --- | --- | --- |
| NS-001-H01 | pergunta | disponibilidade não é capacidade da agenda do gestor | descartado para o roteiro 001 | rascunho |
| NS-001-H02 | pergunta | disponibilidade pertence ao fluxo público | requer reenquadramento para o fluxo público | rascunho |
| NS-001-H03 | pergunta | visões dia/semana/mês confirmadas no código; centralização sem execução autenticada | rascunho — sem descarte por evidência | rascunho |
| NS-001-H04 | dor | listagem dos atendimentos do dia confirmada no código; celular pendente | rascunho — sem descarte por evidência | rascunho |
| NS-001-H05 | dor | visão do dia confirmada no código; importação de dados externos inexistente | rascunho — sem descarte por evidência | rascunho |
| NS-001-H06 | dor | lacunas livres não são exibidas na agenda do gestor | não suportado pela agenda do gestor | rascunho |
| NS-001-H07 | diagnóstico | "tem horário livre" é superfície pública | requer reenquadramento para o fluxo público | rascunho |
| NS-001-H08 | diagnóstico | leitura por papéis existe no código; comportamento compartilhado sem execução autenticada | rascunho — sem descarte por evidência | rascunho |
| NS-001-H09 | diagnóstico | legibilidade em tela confirmada no código; em celular pendente | rascunho — sem descarte por evidência | rascunho |
| NS-001-H10 | contraste | registro único e visão do dia confirmados no código | rascunho — sem descarte por evidência | rascunho |
| NS-001-H11 | contraste | "procurar horário disponível" não é tarefa da agenda do gestor | não suportado pela agenda do gestor | rascunho |
| NS-001-H12 | contraste | checagem de lacuna e de conflito não comprovadas na tela do gestor | não suportado pela agenda do gestor | rascunho |
| NS-001-H13 | curiosidade | elementos da tela inventariados no código; filtros e visões pendentes de execução | rascunho — sem descarte por evidência | rascunho |
| NS-001-H14 | curiosidade | elementos da tela inventariados no código; legibilidade real pendente | rascunho — sem descarte por evidência | rascunho |
| NS-001-H15 | curiosidade | campos de horário, cliente, profissional, serviço, preço e status confirmados no código | rascunho — selecionado para o roteiro 001 | rascunho |

Nenhum hook desta tabela é vencedor ou aprovado. A classificação registra somente o que a evidência técnica permite ou não permite afirmar; desempenho dos hooks segue desconhecido.

## Candidatos para revisão editorial

Cinco hooks haviam seguido para leitura editorial na versão 0.1. A validação técnica reclassificou três deles, porque a formulação original depende de disponibilidade. **Candidatos a revisão, não a aprovação.** Nenhuma escolha aqui declara desempenho superior.

### NS-001-H01

- **Por que é claro:** pergunta curta, direta e compreensível para qualquer responsável por agenda.
- **Conexão com o briefing:** era a formulação registrada como permitida na seção 4 do briefing em 0.1; o briefing 0.2 a substituiu.
- **Validação que falta:** nenhuma — a questão foi encerrada pela evidência: a agenda do gestor não exibe horários disponíveis.
- **Situação após a evidência técnica:** saiu da lista de candidatos; classificação "descartado para o roteiro 001". Texto original preservado na entrada da categoria pergunta.

### NS-001-H06

- **Por que é claro:** nomeia a diferença entre saber que o dia está cheio e saber onde há espaço.
- **Conexão com o briefing:** o briefing 0.2 removeu "espaços disponíveis" do impacto operacional, porque essa leitura não é capacidade da tela do gestor.
- **Validação que falta:** nenhuma para o trecho de lacunas — confirmado como não suportado.
- **Situação após a evidência técnica:** saiu da lista de candidatos; classificação "não suportado pela agenda do gestor", com texto revisado proposto disponível.

### NS-001-H07

- **Por que é claro:** usa formulação condicional e fala do esforço de procurar, não do salão.
- **Conexão com o briefing:** apoia a dor de acompanhamento, mas a pergunta original é de disponibilidade.
- **Validação que falta:** nenhuma para o objeto da pergunta; a superfície correta é o fluxo público do cliente.
- **Situação após a evidência técnica:** saiu da lista de candidatos como formulação original; classificação "requer reenquadramento para o fluxo público".

### NS-001-H10

- **Por que é claro:** contrasta dois processos em uma frase curta, sem julgar pessoas.
- **Conexão com o briefing:** dialoga com a solução proposta de concentrar e visualizar os agendamentos.
- **Validação que falta:** execução autenticada da visão do dia no navegador — a existência está confirmada no código, o comportamento executado não.
- **Interpretação a evitar:** ler como "certo versus errado" ou "profissional versus amador".
- **Situação após a evidência técnica:** segue candidato; não selecionado nesta versão.

### NS-001-H15

- **Por que é claro:** pergunta sobre a leitura do dia e termina apontando para a demonstração, alinhado ao CTA do briefing.
- **Conexão com o briefing:** corresponde à dor da versão 0.2 — visualizar e acompanhar os agendamentos com clareza.
- **Validação que falta:** execução autenticada da tela; os campos citados já estão entre as capacidades confirmadas no código.
- **Interpretação a evitar:** prometer mais clareza como resultado garantido.
- **Situação após a evidência técnica:** **selecionado para o roteiro 001**, com texto revisado; status rascunho, sem aprovação.

Candidaturas que não estavam nesta lista em 0.1 e que a evidência técnica mantém elegíveis, para revisão em tarefa futura: NS-001-H03, NS-001-H04, NS-001-H05, NS-001-H08, NS-001-H09, NS-001-H13, NS-001-H14. Nenhuma delas foi selecionada agora; a seleção é única por decisão desta etapa.

---

## Restrições registradas para esta biblioteca

Nenhum hook pode evoluir para roteiro, legenda, vídeo ou publicação afirmando: redução automática de faltas, prevenção de no-show, confirmação automática, mensagens automáticas, lembretes automáticos, preenchimento automático da agenda, agenda sempre cheia, aumento garantido de ocupação ou de faturamento, controle financeiro, resultado comercial comprovado ou integração não verificada.

A estas restrições soma-se, a partir da evidência técnica, a proibição de apresentar como capacidade da agenda do gestor: exibição de horários disponíveis ou slots livres, criação, edição, remarcação, exclusão, duração como campo próprio e preenchimento automático. Essas quatro primeiras são tarefas da superfície pública do cliente ou não existem na tela autenticada.

Sobre lembretes e notificações: a proibição comercial continua válida, mas o motivo técnico mudou de redação. O Salao02 contém implementação técnica de notificações e lembrete de 24 horas, com implantação, configuração dos canais e entrega real não validadas para esta campanha; nada neste documento autoriza prometer ou demonstrar essas capacidades, e nenhum reminder pode aparecer em narração ou texto de tela.

Desempenho destes hooks é desconhecido: nenhum foi publicado nem medido.

---

## Seleção editorial para o roteiro 001

- **Hook selecionado:** NS-001-H15
- **Texto original:** "Quais informações, na agenda, ajudam a acompanhar os atendimentos sem reconstruir o dia de memória?"
- **Texto revisado:** "Você consegue visualizar os agendamentos do seu salão com clareza?"
- **Categoria:** curiosidade (categoria registrada do hook); o texto revisado tem forma de pergunta direta.
- **Motivo da seleção:** é o hook existente cujo sentido exige o menor ajuste para a campanha revisada — fala de acompanhar os atendimentos pela agenda, sem depender de disponibilidade, slots livres ou automação. Encerra apontando para a demonstração, alinhado ao CTA "Conheça a agenda do Marca Salão." A revisão foi feita por evidência técnica, não por ranking: nenhum hook foi publicado ou medido.
- **Evidência técnica:** [VALIDACAO-FUNCIONAL-AGENDA.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md), seções 4, 5 e 9 — leitura de código e testes selecionados do repositório `Jonatasbottaro/Salao02`, branch `codex/release-evidence`, commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee`. As capacidades de visualização usadas pelo hook (dia, semana, mês, filtros, busca, detalhes com horário, cliente, profissional, serviço, preço e status) estão entre as confirmadas no código.
- **Relação com o briefing:** corresponde à dor da versão 0.2 ("dificuldade de visualizar e acompanhar os agendamentos do salão com clareza"), à pergunta principal da seção 4 e à mensagem principal da seção 8.
- **Principal risco:** prometer "mais clareza" como resultado garantido do uso do sistema, ou ser lido como se a agenda reunisse informações que nunca foram registradas nela.
- **Validação ainda necessária:** execução autenticada da tela em ambiente local com emuladores e dados fictícios — renderização, filtros, busca, modal e ações de status ainda não foram observados em navegador; captura atualizada; comportamento em celular.
- **Status da seleção:** selecionado para roteiro em rascunho
- **Aprovação para produção:** não
- **Data da revisão:** 2026-11-02
- **Responsável:** pendente de definição

**Seleção anterior — histórico, não usar como mensagem atual.** Em 2026-11-02 (versão 0.1 desta biblioteca) o hook selecionado foi NS-001-H01, com o texto "Você sabe quais horários ainda estão disponíveis no seu salão?". A seleção foi **revisada por evidência técnica**: a validação classificou a exibição de horários disponíveis como capacidade não suportada pela agenda do gestor, pertencente ao fluxo público do cliente. O ID, o texto original, o motivo da escolha anterior e a data permanecem registrados na entrada NS-001-H01 e na tabela de triagem.

O hook NS-001-H15 permanece com `Status: rascunho` na lista da categoria curiosidade. Selecionar para roteiro não aprova para publicação: o briefing continua em validação, a biblioteca continua sem autorização de produção e nenhum hook desta tarefa foi aprovado.
