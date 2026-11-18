# Variação Opcional de Hook — NS-002-H02 (Redução de Carga Cognitiva)

- **Campanha:** NS-002 (`Agendamento online no Marca Salão`)
- **Briefing de referência:** [`briefing.md`](briefing.md)
- **Biblioteca de hooks:** [`../../../02-hooks/campanhas/NS-002/hooks.md`](../../../02-hooks/campanhas/NS-002/hooks.md)
- **Roteiro principal:** [`../../../03-roteiros/campanhas/NS-002/roteiro-001.md`](../../../03-roteiros/campanhas/NS-002/roteiro-001.md) (mantém `NS-002-H01` intacto)
- **Status:** rascunho opcional (alternativa para testes A/B ou derivações futuras; não substitui `NS-002-H01`)
- **Data:** 2026-11-18
- **Aprovação para gravação/publicação:** não

---

## 1. Formulação da variação (`NS-002-H02`)

- **ID:** `NS-002-H02`
- **Foco editorial:** redução de carga cognitiva e interrupções operacionais no atendimento presencial.
- **Texto principal:**
  > *"Quantas vezes você parou um atendimento hoje só para responder 'que horas tem livre?'"*
- **Pergunta complementar histórica (preservada de `hooks.md` v0.1):**
  > *"Depois que a cliente confirma, onde esse atendimento aparece para o salão?"*

## 2. Racional editorial e conexão com a jornada técnica

1. **Alívio cognitivo sem promessa de automação:** a dor abordada é a interrupção manual durante um atendimento em andamento para consultar disponibilidade. A resposta visual na peça aponta para o fluxo público `/booking/[salonId]`, onde a cliente visualiza os horários livres calculados pela interface, escolhe o serviço, o profissional e confirma — enquanto o salão acompanha o registro na rota `/gestor/agenda`.
2. **Separação de superfícies preservada:**
   - `/booking/[salonId]`: cálculo e exibição pública de horários livres para a cliente escolher.
   - `/gestor/agenda`: visualização e atualização manual de status pelo gestor (não calcula disponibilidade nem promete criação automática).

## 3. Aderência estrita aos Guardrails NS-002

- **Sem automação de mensagens:** NÃO promete robô de WhatsApp, resposta automática, lembrete de 24h ou confirmação via WhatsApp/SMS/e-mail. A cliente consulta o link de agendamento online; o salão não promete envio automático.
- **Sem promessa financeira ou de no-show:** NÃO promete aumento de faturamento, agenda cheia ou redução de faltas. Trata apenas da clareza operacional e visibilidade da rotina.
- **Sem tela de pagamento:** o fluxo demonstrado encerra na confirmação do agendamento e visualização em `/gestor/agenda`.
- **Preservação do Hook Oficial (`NS-002-H01`):** o hook oficial aprovado para o Roteiro 001 e para o piloto `ns002-piloto-01` permanece integralmente como `NS-002-H01` (*"Como um horário escolhido pela cliente chega à agenda do salão?"*).
