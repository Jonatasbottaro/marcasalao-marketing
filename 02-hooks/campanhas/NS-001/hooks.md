# Hooks da campanha NS-001

- Campanha: NS-001
- Briefing: [../../../00-briefings/campanhas/NS-001/briefing.md](../../../00-briefings/campanhas/NS-001/briefing.md)
- Status do briefing: em validação
- Status desta biblioteca: rascunho
- Versão: 0.1
- Aprovação: pendente
- Uso em produção: não autorizado

> **Estes hooks são rascunhos editoriais. A campanha NS-001 ainda depende da validação funcional da agenda. Nenhum hook deste documento está aprovado para publicação ou produção.**

Contexto de produto que vale para todos os hooks abaixo: o Marca Salão **não possui** mensagens, lembretes ou confirmações automáticas, não envia WhatsApp, SMS ou e-mail de forma automática, não tem automação validada para reduzir no-show e não preenche automaticamente horários vagos. Nenhum texto aqui pode sugerir ou deixar implícita a existência dessas capacidades.

---

## Categoria: pergunta

### NS-001-H01

- **ID:** NS-001-H01
- **Categoria:** pergunta
- **Texto:** "Você sabe quais horários ainda estão disponíveis no seu salão?"
- **Público pretendido:** pessoas responsáveis pela gestão de salões de beleza que organizam a própria agenda.
- **Dor abordada:** falta de clareza sobre a ocupação da agenda e sobre os espaços livres do dia.
- **Continuação sugerida:** mostrar a tela da agenda e percorrer a grade do dia, apontando onde os atendimentos aparecem.
- **Evidência necessária:** validação funcional de que a agenda do Marca Salão exibe os horários disponíveis de forma legível. A captura `01-insta-stories/05_agenda.png` mostra a grade de um dia, mas não comprova por si só esse comportamento.
- **Risco de interpretação:** ser lido como se o sistema avisasse ou apontasse sozinho os buracos da agenda.
- **Status:** rascunho
- **Observações:** é a formulação registrada como permitida no briefing NS-001, seção 4; o uso em produção continua condicionado à validação da visualização.

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

---

## Triagem para a próxima etapa

| ID | Categoria | Depende de validação funcional? | Principal risco | Status |
| --- | --- | --- | --- | --- |
| NS-001-H01 | pergunta | sim — exibição de horários disponíveis | ler como alerta automático do sistema | rascunho |
| NS-001-H02 | pergunta | sim — consulta do dia, inclusive em celular | sugerir que o sistema responde ao cliente | rascunho |
| NS-001-H03 | pergunta | sim — centralização dos registros | insinuar importação de dados externos | rascunho |
| NS-001-H04 | dor | sim — listagem dos atendimentos do dia | escalar a dor para afirmação financeira | rascunho |
| NS-001-H05 | dor | sim — visão completa do dia | desvalorizar o caderno ou soar crítica | rascunho |
| NS-001-H06 | dor | sim — legibilidade dos intervalos livres | sugerir detecção automática de espaços | rascunho |
| NS-001-H07 | diagnóstico | sim, apenas na demonstração que a segue | diagnosticar o salão como desorganizado | rascunho |
| NS-001-H08 | diagnóstico | sim — permissões e visualização compartilhada | prometer multiusuário ou sincronização | rascunho |
| NS-001-H09 | diagnóstico | sim — legibilidade e uso em celular | tratar "visão centralizada" como fato | rascunho |
| NS-001-H10 | contraste | sim — registro único e visão do dia | virar julgamento de certo versus errado | rascunho |
| NS-001-H11 | contraste | sim — fluxo real de consulta | insinuar consulta automática ou instantânea | rascunho |
| NS-001-H12 | contraste | sim — localização de um horário | sugerir prevenção automática de conflitos | rascunho |
| NS-001-H13 | curiosidade | sim — inventário dos elementos da tela | citar funcionalidade não testada | rascunho |
| NS-001-H14 | curiosidade | sim — elementos presentes e legíveis | escorregar para promessa de resultado | rascunho |
| NS-001-H15 | curiosidade | sim — campos exibidos na agenda | transformar expectativa em garantia | rascunho |

Nenhum hook desta tabela é vencedor, descartado ou aprovado. A triagem registra apenas o que ainda falta antes de qualquer avanço.

## Candidatos para revisão editorial

Cinco hooks seguem para leitura editorial. **Candidatos a revisão, não a aprovação.** Nenhuma escolha aqui declara desempenho superior.

### NS-001-H01

- **Por que é claro:** pergunta curta, direta e compreensível para qualquer responsável por agenda.
- **Conexão com o briefing:** é a formulação registrada como permitida na seção 4 do briefing NS-001.
- **Validação que falta:** confirmar que a agenda exibe os horários disponíveis de forma legível.
- **Interpretação a evitar:** deixar parecer que o sistema sinaliza ou avisa os espaços vagos.

### NS-001-H06

- **Por que é claro:** nomeia a diferença entre saber que o dia está cheio e saber onde há espaço.
- **Conexão com o briefing:** corresponde ao impacto operacional "menor clareza sobre espaços disponíveis".
- **Validação que falta:** conferir se a grade do dia torna os intervalos sem atendimento visíveis.
- **Interpretação a evitar:** insinuar que o sistema preenche ou oferece automaticamente esses intervalos.

### NS-001-H07

- **Por que é claro:** usa formulação condicional e fala do esforço de procurar, não do salão.
- **Conexão com o briefing:** apoia a dor principal de falta de clareza sobre a ocupação da agenda.
- **Validação que falta:** nenhum item para a pergunta; a demonstração subsequente depende da consulta validada.
- **Interpretação a evitar:** soar como diagnóstico de desorganização do estabelecimento.

### NS-001-H10

- **Por que é claro:** contrasta dois processos em uma frase curta, sem julgar pessoas.
- **Conexão com o briefing:** dialoga com a solução proposta de concentrar e visualizar os agendamentos.
- **Validação que falta:** confirmar que a agenda exibe o dia inteiro dos registros feitos no sistema.
- **Interpretação a evitar:** ler como "certo versus errado" ou "profissional versus amador".

### NS-001-H15

- **Por que é claro:** termina apontando para a demonstração, alinhado ao CTA do briefing.
- **Conexão com o briefing:** reforça o objetivo de gerar interesse em conhecer a agenda e solicitar demonstração.
- **Validação que falta:** conferir na tela quais campos realmente sustentam a leitura proposta.
- **Interpretação a evitar:** prometer mais clareza como resultado garantido.

---

## Restrições registradas para esta biblioteca

Nenhum hook pode evoluir para roteiro, legenda, vídeo ou publicação afirmando: redução automática de faltas, prevenção de no-show, confirmação automática, mensagens automáticas, lembretes automáticos, preenchimento automático da agenda, agenda sempre cheia, aumento garantido de ocupação ou de faturamento, controle financeiro, resultado comercial comprovado ou integração não verificada.

Desempenho destes hooks é desconhecido: nenhum foi publicado nem medido.

---

## Seleção editorial para o roteiro 001

- **Hook selecionado:** NS-001-H01
- **Texto:** "Você sabe quais horários ainda estão disponíveis no seu salão?"
- **Categoria:** pergunta
- **Motivo da seleção:** é a formulação registrada como permitida pelo briefing NS-001 (seções 4 e 9), tem frase curta e natural, aponta para uma ação que pode ser demonstrada na tela da agenda e tem continuidade direta para um roteiro curto. Os outros quatro candidatos também seguem válidos para revisão; esta escolha é de rota de escrita, não de ranking.
- **Relação com a dor do briefing:** corresponde à dor principal declarada na seção 4 — falta de clareza sobre a ocupação da agenda e sobre a existência de horários vazios.
- **Continuação possível:** abrir a agenda do dia e percorrer a grade, mostrando os atendimentos registrados — restrito ao que uma tela validada realmente exibe.
- **Evidência funcional necessária:** validar que a agenda exibe os horários disponíveis de forma legível, item que está em "Pendente de validação" na seção 7 do briefing. Sem essa validação, o hook não pode virar peça gravada.
- **Principal risco de interpretação:** ser lido como se o sistema sinalizasse ou avisasse sozinho os espaços vagos da agenda.
- **Status da seleção:** selecionado para roteiro em rascunho
- **Aprovação para produção:** não
- **Data da seleção:** 2026-11-02
- **Responsável pela seleção:** pendente de definição, se não estiver documentado

O hook NS-001-H01 permanece com `Status: rascunho` na lista acima. Selecionar para roteiro não aprova para publicação: o briefing continua em validação e a biblioteca continua sem autorização de produção.
