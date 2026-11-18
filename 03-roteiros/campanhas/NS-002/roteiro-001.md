# Roteiro 001 — Agendamento online no Marca Salão

- Campanha: NS-002
- Briefing: [../../../00-briefings/campanhas/NS-002/briefing.md](../../../00-briefings/campanhas/NS-002/briefing.md)
- Biblioteca de hooks: [../../../02-hooks/campanhas/NS-002/hooks.md](../../../02-hooks/campanhas/NS-002/hooks.md)
- Adaptação para Stories: [stories-001.md](stories-001.md)
- Hook selecionado: NS-002-H01
- Status do briefing: em validação — aprovação editorial parcial em 2026-11-16
- Status do hook: rascunho — selecionado para o roteiro 001
- Status do roteiro: rascunho
- Versão: 0.1
- Data: 2026-11-16
- Aprovação: pendente para produção
- Duração-alvo: **30 segundos** (faixa aprovada: 25–35 s)
- Autorizado para capturas, gravação ou publicação: **não**

> **Rascunho editorial.** A jornada foi executada em ambiente local com emuladores e dados fictícios em 2026-11-05, mas este roteiro não autoriza capturas, gravação, renderização, agendamento nem publicação. A narração existe apenas como texto; o vídeo final será sem áudio, com legendas visíveis e `.srt`, conforme [../../../WORKFLOW.md](../../../WORKFLOW.md).

---

## 1. Objetivo

Mostrar a continuidade entre a escolha feita pela cliente e o registro visível na agenda do salão, usando somente comportamento confirmado na jornada local. Resultado pretendido: despertar interesse em conhecer o agendamento online do Marca Salão.

Não prometer: pagamento como benefício, mensagens ou confirmações automáticas, lembretes, redução de faltas, ocupação garantida ou aumento de faturamento.

## 2. Público

- Pessoas que gerenciam salões de beleza.
- Responsáveis por organizar serviços, equipe e agenda.
- Contexto: uma cliente escolhe um horário e o salão precisa localizar esse atendimento na própria agenda.

## 3. Hook selecionado

- **ID:** NS-002-H01
- **Categoria:** pergunta
- **Texto:** "Como um horário escolhido pela cliente chega à agenda do salão?"
- **Decisão:** definido pelo titular em 2026-11-16 como abertura da peça.
- **Risco de interpretação:** "chega" pode ser lido como automação. Na demonstração, significa que o agendamento criado no fluxo público aparece na agenda do gestor — fato observado no teste local.
- **Evidência:** execução autenticada de 2026-11-05 e reconferência de código no Salao02 HEAD `91bb5e0`.

## 4. Formato proposto

- Canal inicial: Instagram Reels; adaptação em três Stories no arquivo [stories-001.md](stories-001.md).
- Formato: vertical 9:16, 1080 × 1920, 30 fps, sem áudio.
- Duração: 30 s, dentro da faixa de 25–35 s.
- Legendas: visíveis e sincronizadas; `.srt` e texto de narração separado entregues na etapa de legendas, não nesta rodada.
- Textos de tela e narração em português do Brasil, com **Marca Salão**.

## 5. Estrutura aprovada

```
Pergunta de abertura → A cliente escolhe → A cliente confirma → O salão vê → CTA
```

- **Meus Agendamentos** fica como **evidência de apoio**, não como cena obrigatória. O corte da confirmação para `/gestor/agenda` já estabelece a ligação entre as duas pontas.
- **Pagamento simulado** fica fora da peça: sem menção, sem tela de cobrança e sem benefício associado.
- A interface capturada mostra **Meu Salão**; os textos usam **Marca Salão**. Resolver a diferença antes das capturas finais.

## 6. Roteiro por cenas

| # | Tempo | Momento | Texto de tela | Narração proposta | Visual e evidência |
| --- | --- | --- | --- | --- | --- |
| 1 | 0:00–0:04 (4 s) | Abertura | "Como um horário escolhido pela cliente chega à agenda do salão?" | "Como um horário escolhido pela cliente chega à agenda do salão?" | Arte de marca, sem produto. Hook NS-002-H01. |
| 2 | 0:04–0:10 (6 s) | 1 — A cliente escolhe | "A cliente escolhe o serviço e o profissional." | "A cliente informa os dados, escolhe o serviço e o profissional." | `/booking/[salonId]`: dados fictícios, cartão de serviço e cartão de profissional. E2E etapas 2–4. |
| 3 | 0:10–0:17 (7 s) | 2 — A cliente confirma | "Seleciona o horário disponível e confirma." | "Na sequência, escolhe um horário disponível e confirma o agendamento." | Calendário, slot `HH:MM` habilitado e botão "Confirmar Agendamento". E2E etapas 5–7. Sem tela de pagamento. |
| 4 | 0:17–0:20 (3 s) | Ponte | "Agendamento realizado." | "E o mesmo registro segue para a agenda do salão." | Mensagem de sucesso da interface. Inserto opcional de 1 s de **Meus Agendamentos** como apoio, sem virar cena obrigatória. |
| 5 | 0:20–0:26 (6 s) | 3 — O salão vê | "O mesmo atendimento aparece na agenda do salão." | "O mesmo atendimento aparece na agenda do salão." | `/gestor/agenda` com o mesmo serviço, cliente e profissional fictícios. E2E etapa 9 e verificação manual de 2026-11-05. |
| 6 | 0:26–0:30 (4 s) | CTA | "Conheça o agendamento online no Marca Salão" + `marcasalao.com.br` | "Conheça o agendamento online no Marca Salão. marcasalao.com.br" | Arte final de marca; sem botão clicível desenhado. |

**Total: 30 segundos.**

### Notas por cena

- **Cena 2:** mostrar somente a escolha. Não afirmar que a cliente dispensa conta — o acesso sem login permanece pendente no briefing.
- **Cena 3:** mostrar a seleção de horário e a confirmação. Não citar pagamento, não exibir cobrança e não transformar mock em benefício.
- **Cena 4:** "Meus Agendamentos" é apoio opcional; se usado, ocupa até 1 s dentro destes 3 s, sem acrescentar momento nem alterar a duração total.
- **Cena 5:** usar captura nova com fixture editorial. Não reaproveitar namespace E2E, preço de R$ 12.000,00, menu administrativo amplo nem enquadramento de validação.
- **Cena 6:** `marcasalao.com.br` é texto. Bio, sticker e rastreamento seguem pendentes de confirmação.

## 7. Texto corrido de narração

> Como um horário escolhido pela cliente chega à agenda do salão?
>
> A cliente informa os dados, escolhe o serviço e o profissional.
>
> Na sequência, escolhe um horário disponível e confirma o agendamento.
>
> E o mesmo registro segue para a agenda do salão.
>
> O mesmo atendimento aparece na agenda do salão.
>
> Conheça o agendamento online no Marca Salão. marcasalao.com.br

A narração acima é texto de apoio para geração externa de áudio. Nenhum áudio é gerado nesta rodada.

## 8. Textos na tela

1. "Como um horário escolhido pela cliente chega à agenda do salão?"
2. "A cliente escolhe o serviço e o profissional."
3. "Seleciona o horário disponível e confirma."
4. "Agendamento realizado."
5. "O mesmo atendimento aparece na agenda do salão."
6. "Conheça o agendamento online no Marca Salão" + `marcasalao.com.br`

## 9. Plano de demonstração

| Momento | Tela | Evidência | O que não mostrar |
| --- | --- | --- | --- |
| A cliente escolhe | `/booking/[salonId]` — serviço e profissional | E2E local 2026-11-05, etapas 2–4 | Dados reais, nomes E2E, promessa de conta opcional |
| A cliente confirma | Calendário, horário disponível e confirmação | E2E local 2026-11-05, etapas 5–7 | Pagamento, cobrança, automação de contato |
| O salão vê | `/gestor/agenda` | E2E etapa 9 e verificação manual | Slots livres, criação/edição pela agenda, namespace de teste |
| Apoio opcional | `/cliente/bookings` — Meus Agendamentos | E2E etapa 8 | Uso como cena obrigatória ou promessa de benefício |

## 10. Materiais necessários

- Artes de abertura e CTA na identidade do Marca Salão.
- Capturas novas com fixture editorial de dados fictícios: serviço, profissional, calendário, confirmação e agenda do gestor.
- Narração em texto separado e `.srt` sincronizado — etapa posterior, não incluída neste rascunho.
- Sem áudio original, narração, música ou efeito no editor; exportação preferida com `-an`.

## 11. Proteção de dados e marca

- Usar somente dados fictícios, completos e plausíveis; sem telefone, e-mail, credencial ou identificador real.
- Não exibir console, ferramentas de desenvolvedor, namespace `e2e-...` ou ambiente de produção.
- Textos usam **Marca Salão**. A interface capturada exibe **Meu Salão**; resolver antes das capturas finais sem editar a tela sem autorização.
- Não prometer acesso direto ao painel `/gestor`, que exige credenciais fora do repositório.

## 12. Pendências

- [ ] Confirmar link externo do perfil antes de usar "link na bio" no Reels.
- [ ] Definir rastreamento; manter "não rastreado" até decisão.
- [ ] Sticker de link depende de autorização de publicação.
- [ ] Criar fixture editorial e indicar responsável, commit do Salao02 e ambiente das capturas.
- [ ] Resolver "Marca Salão" vs. "Meu Salão" na interface antes das capturas.
- [ ] Revisar e aprovar textos de tela e narração.
- [ ] Cronometrar a leitura e confirmar os 30 s.
- [ ] Autorizar separadamente capturas, gravação e publicação.

## 13. Checklist editorial

- [x] Briefing com aprovação parcial registrada.
- [x] Hook selecionado e vinculado a este roteiro.
- [x] Três momentos mantidos, na ordem aprovada.
- [x] Meus Agendamentos classificado como evidência de apoio.
- [x] Pagamento simulado fora da peça.
- [x] CTA com "Conheça o agendamento online no Marca Salão" e `marcasalao.com.br`.
- [x] Sem mensagens, lembretes ou confirmações automáticas.
- [ ] Fixture e capturas preparadas — pendente.
- [ ] Textos revisados e duração conferida — pendente.
- [ ] Autorização de produção — pendente.

## 14. Aprovação

- Elaborado por: agente de marketing do Marca Salão, em 2026-11-16.
- Revisado por: pendente.
- Aprovado para produção: não.
- Autorizado para gravação: não.
- Autorizado para publicação: não.
- Observações: rascunho pronto para revisão do titular. A aprovação parcial do briefing autorizou apenas avançar aos rascunhos de hooks e roteiro.
