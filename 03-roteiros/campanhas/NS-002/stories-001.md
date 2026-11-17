# Stories 001 — Agendamento online no Marca Salão

- Campanha: NS-002
- Briefing: [../../../00-briefings/campanhas/NS-002/briefing.md](../../../00-briefings/campanhas/NS-002/briefing.md)
- Roteiro Reels: [roteiro-001.md](roteiro-001.md)
- Hook selecionado: NS-002-H01
- Status: rascunho
- Versão: 0.1
- Data: 2026-11-16
- Aprovação para produção: não
- Autorizado para capturas, gravação ou publicação: **não**

> Adaptação em **três Stories** do mesmo recorte aprovado para o Reels. Sem áudio, sem pagamento simulado na peça e sem botão clicível desenhado. **Marca Salão** nos textos; a diferença para **Meu Salão** na interface permanece sinalizada para resolução antes das capturas.

## Estrutura aprovada

1. Pergunta de abertura.
2. A cliente escolhe e confirma — momentos 1 e 2 compactados.
3. O salão vê e CTA — momento 3 com chamada final.

A tela **Meus Agendamentos** é evidência de apoio, não painel obrigatório. O corte da confirmação para a agenda do gestor já mostra a ligação entre as duas pontas.

---

## Story 1 — Abertura

- **Texto da tela:** "Como um horário escolhido pela cliente chega à agenda do salão?"
- **Visual:** fundo na identidade do Marca Salão, texto em destaque, sem produto.
- **Interação:** nenhuma obrigatória; enquete apenas se aprovada em revisão posterior.
- **Evidência:** hook NS-002-H01, definido pelo titular em 2026-11-16.
- **Risco:** ler "chega" como automação. O texto de tela não cita envio, mensagem ou confirmação automática.

## Story 2 — A cliente escolhe e confirma

- **Texto da tela:** "A cliente escolhe o serviço, o profissional e o horário — e confirma."
- **Visual:** microsequência dentro do mesmo Story, com dados fictícios: cartão de serviço, cartão de profissional, calendário com horário disponível e mensagem "Agendamento realizado".
- **Ação única por quadro:** um elemento por vez; sem tela de pagamento e sem cobrança.
- **Evidência:** E2E local de 2026-11-05, etapas 2–7; reconferência de código no Salao02 HEAD `91bb5e0`.
- **Risco:** sugerir que a cliente não precisa de conta ou que o sistema envia algo automaticamente. Ambos ficam fora do texto.

## Story 3 — O salão vê e CTA

- **Texto da tela:** "O mesmo atendimento aparece na agenda do salão. Conheça o agendamento online no Marca Salão. marcasalao.com.br"
- **Visual:** corte da confirmação para `/gestor/agenda`, com o mesmo serviço, cliente e profissional fictícios; fecha em arte de marca com o CTA.
- **Evidência de apoio opcional:** inserto curto de **Meus Agendamentos** entre a confirmação e a agenda, sem se tornar tela obrigatória.
- **CTA:** "Conheça o agendamento online no Marca Salão" com `marcasalao.com.br` como texto.
- **Risco:** desenhar botão clicível ou tratar sticker como presente. Nenhum dos dois faz parte do texto principal.

---

## Textos prontos para revisão

1. "Como um horário escolhido pela cliente chega à agenda do salão?"
2. "A cliente escolhe o serviço, o profissional e o horário — e confirma."
3. "O mesmo atendimento aparece na agenda do salão. Conheça o agendamento online no Marca Salão. marcasalao.com.br"

## Pendências

- [ ] Confirmar link externo do perfil antes de usar "link na bio".
- [ ] Autorizar sticker de link antes de usá-lo; não inferir que botão desenhado cria sticker.
- [ ] Definir rastreamento; manter "não rastreado" até decisão.
- [ ] Criar fixture editorial e capturas com dados fictícios; resolver "Marca Salão" vs. "Meu Salão" na interface antes das capturas finais.
- [ ] Revisar textos, duração por tela e aprovar a sequência.
- [ ] Autorizar separadamente capturas, gravação e publicação.

## Checklist editorial

- [x] Três Stories, na ordem aprovada.
- [x] Mesmo hook do Reels.
- [x] Três momentos preservados, com os dois primeiros compactados no Story 2.
- [x] Meus Agendamentos como evidência de apoio.
- [x] Pagamento simulado fora da peça.
- [x] CTA com frase e domínio como texto.
- [x] Sem automações de contato ou resultados garantidos.
- [ ] Capturas e autorização de produção — pendentes.
