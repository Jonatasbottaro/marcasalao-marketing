# Hooks da campanha NS-002 — Agendamento online no Marca Salão

- Campanha: NS-002
- Briefing: [../../../00-briefings/campanhas/NS-002/briefing.md](../../../00-briefings/campanhas/NS-002/briefing.md)
- Validação funcional: [../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md)
- Validação por execução: [../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md](../../../00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md)
- Status do briefing: em validação, com aprovação editorial parcial em 2026-11-16 para hooks e roteiro
- Status desta biblioteca: rascunho
- Versão: 0.1
- Data: 2026-11-16
- Aprovação: parcial — abertura definida pelo titular; nenhum hook foi publicado ou medido
- Uso em produção: não autorizado

> **Dois rascunhos de abertura para o Reels e os Stories.** A pergunta NS-002-H01 foi definida pelo titular em 2026-11-16 e é a usada no roteiro 001. Nenhuma afirmação de desempenho é feita: não há publicação nem medição.

Contexto comum a todas as opções:

- Público: quem gerencia salões de beleza.
- Demonstração comprovada: a cliente escolhe serviço e profissional, seleciona horário disponível e confirma; o mesmo atendimento aparece na agenda do gestor.
- Textos de marca: **Marca Salão**. A interface capturada mostra **Meu Salão**; resolver a diferença antes das capturas finais.
- Pagamento mock existe apenas na evidência de teste e fica fora da peça.
- Não prometer mensagens, lembretes ou confirmações automáticas, redução de faltas, ocupação garantida nem aumento de faturamento.
- `marcasalao.com.br` é texto; "link na bio" e sticker dependem de confirmação separada.

---

## NS-002-H01 — selecionado para o roteiro 001

- **ID:** NS-002-H01
- **Categoria:** pergunta
- **Texto:** "Como um horário escolhido pela cliente chega à agenda do salão?"
- **Público pretendido:** gestores de salões de beleza que acompanham a agenda do estabelecimento.
- **Dor abordada:** necessidade de ver a ligação entre o que a cliente escolheu e o que ficou registrado para o salão.
- **Continuação sugerida:** abrir com arte de marca, percorrer os três momentos e encerrar com o mesmo atendimento em `/gestor/agenda`.
- **Evidência que sustenta:** jornada E2E local de 2026-11-05 — agendamento pelo fluxo público com pagamento mock, visível para cliente, gestor e profissional; reconferência de código no Salao02 HEAD `91bb5e0`.
- **Risco de interpretação:** ler "chega" como automação ou envio de mensagem ao cliente. Na peça, a chegada é o registro do agendamento na agenda, observado no teste local.
- **Status:** rascunho — selecionado para o roteiro 001 por decisão do titular em 2026-11-16.
- **Observações:** é a abertura aprovada para esta rodada. Não declara desempenho superior.

## NS-002-H02 — opção alternativa (redução de carga cognitiva)

- **ID:** NS-002-H02
- **Categoria:** dor operacional / redução de carga cognitiva
- **Texto:** "Quantas vezes você parou um atendimento hoje só para responder 'que horas tem livre?'"
- **Formulação histórica complementar:** "Depois que a cliente confirma, onde esse atendimento aparece para o salão?" (preservada da v0.1 para continuidade).
- **Documentação dedicada:** [`../../../00-briefings/campanhas/NS-002/NS-002-H02-variacao-carga-cognitiva.md`](../../../00-briefings/campanhas/NS-002/NS-002-H02-variacao-carga-cognitiva.md)
- **Público pretendido:** gestores e profissionais que interrompem atendimentos para consultar horários manualmente e conferem a agenda depois de uma reserva pela cliente.
- **Dor abordada:** carga cognitiva de checar e responder disponibilidade no meio de um atendimento, e dúvida sobre onde consultar o registro gerado no fluxo público.
- **Continuação sugerida:** mostrar a cliente consultando horários livres em `/booking/[salonId]`, confirmando o agendamento e o registro aparecendo em `/gestor/agenda`.
- **Evidência que sustenta:** execução autenticada de 2026-11-05; o cálculo público de horários livres ocorre em `/booking/[salonId]` e o mesmo serviço aparece em `/gestor/agenda` vinculado ao profissional.
- **Risco de interpretação:** sugerir resposta automática por bot no WhatsApp, pagamento ou notificação automática. Todos ficam expressamente fora da peça.
- **Status:** rascunho — variação opcional documentada; `NS-002-H01` permanece intacto como hook selecionado para o roteiro 001.
- **Observações:** alternativa mantida para revisão futura sem alterar a seleção principal. Nenhuma comparação de desempenho é feita.

---

## Seleção para o roteiro 001

- **Hook selecionado:** NS-002-H01.
- **Texto usado:** "Como um horário escolhido pela cliente chega à agenda do salão?"
- **Motivo:** decisão editorial do titular em 2026-11-16. A pergunta leva diretamente à demonstração comprovada no teste local e não depende de funcionalidade pendente.
- **Relação com o briefing:** corresponde à mensagem principal e ao primeiro item das decisões registradas na seção 17.
- **Status da seleção:** selecionado para rascunho de roteiro; não é aprovação de produção.
- **Aprovação para gravação:** não.
- **Aprovação para publicação:** não.

## Restrições registradas

Nenhum hook desta biblioteca pode afirmar ou sugerir pagamento como benefício, envio automático de mensagem, lembrete, confirmação automática, preenchimento automático de horários, redução de faltas, ocupação garantida ou aumento de faturamento. Também não pode tratar o acesso sem conta ou o deep link da página pública como confirmado — ambos permanecem pendentes no briefing.
