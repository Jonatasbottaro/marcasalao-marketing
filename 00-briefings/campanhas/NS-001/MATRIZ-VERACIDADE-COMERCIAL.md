# Matriz de veracidade comercial — NS-001 (24/11/2026)

- Fontes de evidência: [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md) (código + testes selecionados, commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee`, 02/11/2026) e [`VALIDACAO-EXECUCAO-2026-11-05.md`](VALIDACAO-EXECUCAO-2026-11-05.md) (E2E local + Chromium autenticado, 05/11/2026).
- Estados distintos, conforme governança: **implementação ≠ teste ≠ operação real ≠ autorização comercial**.
- "Pode entrar na peça?" considera texto + demonstração; gravação/publicação continuam bloqueadas por aprovação editorial.
- Atualidade do produto: checkout local sem Git; nenhuma revalidação posterior a 05/11 foi possível nesta estação. Toda linha "Confirmado" vale para a evidência histórica e fica **sujeita à conferência atual** antes da gravação (critério de aceite do plano de gravação).

## 1. Matriz de afirmações

| # | Afirmação | Evidência | Status | Pode entrar na peça? |
| --- | --- | --- | --- | --- |
| A1 | Visualizar agendamentos do salão em uma tela (agenda do gestor, `/gestor/agenda`) | Validação §4 (rota, assinatura da coleção) + execução §2 (renderização, carregamento) | Confirmado na evidência histórica | Sim, sujeito à conferência atual |
| A2 | Visões Dia, Semana e Mês do mesmo registro | Validação §4 + teste jsdom `AgendaViewSwitcher.test.tsx` + execução §2 (três visões observadas) | Confirmado na evidência histórica | Sim (cena 3), dados fictícios |
| A3 | Navegação por data e botão "Hoje" | Validação §8 (`DayNavigator.tsx`) + execução §2 | Confirmado na evidência histórica | Sim, como parte da cena 3 |
| A4 | Filtro por profissional | Validação §4 + execução §2 (semana restrita ao profissional selecionado) | Confirmado na evidência histórica | Sim (cena 4) |
| A5 | Filtro por status (Pendente, Confirmado, Concluído, Cancelado, No-show) | Validação §4 + execução §2 (filtro Cancelado observado) | Confirmado na evidência histórica | Sim (cena 4); não prometer filtro inexistente |
| A6 | Busca por nome de cliente | Validação §4 (debounce) + execução §2 | Confirmado na evidência histórica | Sim (cena 4); busca por serviço/período NÃO existe — proibida |
| A7 | Detalhes com horário, cliente, profissional, serviço, preço e status (+ status de pagamento) | Validação §4/§8 (`BookingDetailModal.tsx`) + execução §2 (campos preenchidos) | Confirmado na evidência histórica | Sim (cena 5), somente dados fictícios plausíveis |
| A8 | Confirmação manual de status com persistência | Validação §4 + execução §2 (Pendente→Confirmado, persistiu após recarga; nenhuma mensagem enviada) | Confirmado na evidência histórica | Sim (cena 6), apenas ato manual; sem segunda transição |
| A9 | "Acompanhe os agendamentos do dia, da semana ou do mês em uma agenda organizada" / "Tenha mais clareza…" | Validação §9 "Liberado com ajuste" (formulação de visualização/acompanhamento) | Confirmado como formulação permitida | Sim, como proposta/pergunta, nunca como resultado garantido |
| A10 | Informação do dia espalhada entre caderno/conversa/planilha (cena 2) | Briefing §4/§5 — qualitativo, sem pesquisa | Hipótese editorial condicional | Sim, apenas na forma condicional ("Quando…"); sem estatística, sem universalidade, sem prejuízo financeiro |
| A11 | Agenda legível em celular | Execução §2 (viewport emulado 390×844) | Confirmado em emulação; aparelho físico não testado | Sim, sem prometer desempenho em aparelho físico; não afirmar "testado em celular real" |
| A12 | Exibir horários disponíveis / slots livres na agenda do gestor | Validação §5 — ausência verificada | Não suportado | **Não** |
| A13 | Criar, editar, remarcar ou excluir agendamento pela agenda do gestor | Validação §5 — ausências verificadas | Não suportado | **Não** |
| A14 | Duração como campo próprio da tela | Validação §5 | Não suportado | **Não** |
| A15 | Preenchimento automático da agenda / agenda sempre cheia | Validação §5/§9 | Não suportado | **Não** |
| A16 | Envio de mensagens, lembretes automáticos, confirmação automática de clientes | Validação §7 — implementação técnica existe; implantação/provedores/entrega real pendentes | Implementação confirmada; operação e autorização comercial NÃO | **Não** (nem como promessa, nem como demonstração; não citar reminder/scheduler/provedores) |
| A17 | Redução de faltas / prevenção de no-show / eliminação de no-show | Nenhuma validação operacional | Não suportado | **Não** |
| A18 | Aumento garantido de faturamento ou ocupação | Nenhuma evidência | Não suportado | **Não** |
| A19 | Exportação CSV | Validação §4 (código); conteúdo não inspecionado (proteção de dados) | Confirmado no código; fora do escopo da peça | Não entra na demonstração desta campanha |
| A20 | Multiusuário / controle de acesso compartilhado | Validação §8 (gate de papel) sem teste concorrente | Pendente de validação | **Não** |
| A21 | "O sistema não possui lembretes" (formulação absoluta antiga) | Validação §7 — implementação localizada | Rejeitado anteriormente (impreciso) | **Não** usar nenhuma das duas pontas |
| A22 | Jornada pública do cliente cria agendamento que aparece na agenda do gestor | Execução §1 (jornada E2E 1 passed) | Confirmado na evidência histórica | Não é cena desta campanha; não usar para prometer disponibilidade na tela do gestor |

## 2. Rastreabilidade frase a frase do roteiro-001 v0.3

| Cena | Texto de tela | Narração | Linhas da matriz |
| --- | --- | --- | --- |
| 1 | "Você consegue visualizar os agendamentos do seu salão com clareza?" | idem | A9 (pergunta de reconhecimento; sem garantia) |
| 2 | "Quando as informações ficam espalhadas, cada lugar mostra um pedaço do dia." | "Quando uma parte da agenda fica no caderno, outra na conversa e outra na planilha, reunir as informações pode tomar tempo no meio do atendimento." | A10 (condicional, qualitativa) |
| 3 | "O mesmo registro, visto por dia, semana ou mês." | "Na agenda do painel, o registro é o mesmo: dá para olhar o dia, a semana ou o mês." | A1, A2, A3 |
| 4 | "Filtrar por profissional, por status, ou buscar pelo nome." | "Dá para filtrar por profissional, por status, ou buscar o nome de um cliente." | A4, A5, A6 |
| 5 | "Abrir um atendimento e ver os dados dele." | "Abrindo o atendimento, aparecem o horário, o cliente, o profissional, o serviço, o preço e o status." | A7 |
| 6 | "Atualizar o status do atendimento." | "Quando a gestão confirma o atendimento, o status fica registrado na agenda." | A8 (manual; sem mensagem/automação) |
| 7 | "Conheça a agenda do Marca Salão." | idem | A9 + CTA do briefing §12; destino por canal pendente |

Nenhuma frase do roteiro atual afirma item bloqueado (A12–A18, A20, A21). A narração não cita reminder, scheduler, notificação ou provedor.

## 3. Regras de uso desta matriz

1. Toda nova frase proposta para tela, narração ou legenda deve ser mapeada a uma linha "Sim" antes de entrar no storyboard.
2. Linhas "Confirmado na evidência histórica" exigem conferência atual do produto na sessão de gravação (runbook local com emuladores); divergência encontrada ⇒ bloquear a cena e registrar.
3. Dados fictícios editoriais (fixture dedicada) substituem a massa E2E antes de qualquer frame final; preço de R$ 12.000,00 e identificadores E2E não podem aparecer.
4. Esta matriz não autoriza gravação nem publicação; é insumo do pacote de aprovação.