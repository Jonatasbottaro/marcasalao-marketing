# Validação funcional da agenda — NS-001

## 1. Identificação

- Campanha: NS-001
- Repositório auditado: Jonatasbottaro/Salao02
- Branch auditada: codex/release-evidence
- Commit auditado: 6342a33a36b0a4eadd0f5a62770f1eee485156ee
- Data da validação: 2026-11-02
- Tipo de validação: leitura de código e execução de testes automatizados selecionados
- Aplicação autenticada executada: não
- E2E Playwright executado: não
- Ambiente de staging acessado: não
- Ambiente de produção acessado: não
- Credencial demo utilizada: não
- Dados reais utilizados: não
- Repositório Salao02 alterado: não

## 2. Limites da validação

- Não houve execução autenticada da aplicação.
- Não houve acesso a staging ou produção.
- Não houve uso da credencial demo anteriormente exposta.
- Não houve execução do E2E Playwright.
- Não houve validação em navegador da tela autenticada.
- Não houve validação em dispositivo móvel real.
- Não houve validação real dos filtros no navegador.
- Não houve validação de entrega real por e-mail, SMS, WhatsApp ou push.
- Testes unitários comprovam comportamento isolado, não implantação.
- Código responsivo não comprova funcionamento em dispositivo real.
- O projeto possui runbook de E2E local com emuladores.
- A jornada local ainda precisa ser executada em tarefa independente.
- Nenhuma classificação "confirmado por execução" deve ser atribuída à aplicação completa quando a evidência veio apenas de testes unitários ou jsdom.

Consequência direta destes limites: tudo que está aqui como "confirmado no código" é afirmação sobre o repositório no commit auditado, não sobre o comportamento observado em tela. A coluna "confirmado por teste automatizado" tem alcance ainda mais estreito — vale para a função testada, com mocks, fora de qualquer ambiente publicado.

## 3. Ambientes e segurança

- Development é o ambiente indicado para emuladores e debug.
- Staging é indicado para QA e validação pré-release.
- Production contém tráfego real e está fora do escopo.
- O próximo E2E deve usar Firebase Auth Emulator.
- O próximo E2E deve usar Firestore Emulator.
- O próximo E2E deve usar pagamento local ou mock.
- O próximo E2E deve usar autenticação simulada.
- Nenhuma chave live pode ser usada.
- Nenhuma credencial exposta pode ser reutilizada.
- Nenhum dado real pode aparecer em capturas.
- Valores de `.env` não devem ser lidos, exibidos ou versionados.
- Nenhum deploy, migração ou seed remoto está autorizado.

A documentação de ambientes do Salao02 lista, por nome e sem valores, as variáveis que sustentam jobs internos (`INTERNAL_API_KEY`, `SCHEDULER_API_KEY`, `CRON_API_KEY`, `SCHEDULER_APP_URL`), em `docs/environments.md:70`. Nenhum arquivo `.env` foi aberto durante a validação.

## 4. Capacidades confirmadas no código

Classificação por linha. "Código" = existe no commit auditado; "teste" = comportamento sustentado por teste automatizado executado na auditoria; "autenticado" = só vale depois de abrir a tela num ambiente controlado.

| Capacidade | Evidência no código | Teste automatizado | Execução autenticada |
| --- | --- | --- | --- |
| Rota `/gestor/agenda` | `ROUTE_MAP.md` registra a rota e o arquivo `src/app/(dashboard)/gestor/agenda/page.tsx` | não | pendente |
| Visualização de agendamentos | `gestor/agenda/page.tsx` assina a coleção de agendamentos do salão e deriva a lista exibida | não | pendente |
| Agendamentos ocupados | `CalendarGrid.tsx` posiciona cada atendimento pelo horário de início e fim | não | pendente |
| Visão dia | `AgendaViewSwitcher.tsx` e `CalendarGrid.tsx` | sim — jsdom (`AgendaViewSwitcher.test.tsx`) | pendente |
| Visão semana | idem | sim — jsdom (`AgendaViewSwitcher.test.tsx`) | pendente |
| Visão mês | idem | sim — jsdom (`AgendaViewSwitcher.test.tsx`) | pendente |
| Filtro por profissional | `gestor/agenda/page.tsx` aplica filtro sobre a lista | não | pendente |
| Filtro por status | `gestor/agenda/page.tsx` mantém seletor de status | não | pendente |
| Busca por nome de cliente | `gestor/agenda/page.tsx` filtra por nome do cliente, com debounce | não | pendente |
| Detalhes do agendamento | `BookingDetailModal.tsx` | não | pendente |
| Horário no modal | `BookingDetailModal.tsx` | não | pendente |
| Cliente no modal | `BookingDetailModal.tsx` | não | pendente |
| Profissional no modal | `BookingDetailModal.tsx` | não | pendente |
| Serviço no modal | `BookingDetailModal.tsx` | não | pendente |
| Preço no modal | `BookingDetailModal.tsx` exibe o valor total | não | pendente |
| Status | `BookingCard.tsx` com rótulos e estilos por status | não | pendente |
| Confirmação | `BookingDetailModal.tsx` e `handleStatusUpdate` em `gestor/agenda/page.tsx`, apoiados por `firestore.rules:212` | sim — biblioteca (`bookings.test.ts`) | pendente |
| Conclusão | `BookingDetailModal.tsx` | sim — biblioteca (`bookings.test.ts`) | pendente |
| No-show | `BookingDetailModal.tsx` | não | pendente |
| Cancelamento | `BookingDetailModal.tsx` | sim — `bookings.test.ts` e `api/bookings/cancel/route.test.ts` | pendente |
| Pagamento local | `BookingDetailModal.tsx` e rota `/api/payments/mark-local-paid` | não | pendente |
| Exportação CSV | `gestor/agenda/page.tsx` monta cabeçalho e arquivo | não | pendente |
| Estado vazio | `CalendarGrid.tsx:171` — "Nenhum agendamento no período." | não | pendente |
| Estado de erro | `gestor/agenda/page.tsx` trata falha da conexão em tempo real | não | pendente |
| Estrutura responsiva | `CalendarGrid.tsx:152` — ramo mobile com `md:hidden` | não | pendente |

Leitura da tabela: nenhum item está confirmado por execução autenticada. A coluna de teste cobre comportamento isolado de biblioteca ou de componente em jsdom, não a tela publicada.

## 5. Capacidades não suportadas na agenda do gestor

Ausências verificadas na tela autenticada do gestor, no commit auditado:

- Exibição de slots livres.
- Oferta de horários disponíveis.
- Criação de agendamento.
- Edição de agendamento.
- Remarcação.
- Movimentação de horário.
- Exclusão.
- Duração como campo próprio da tela.
- Preenchimento automático da agenda.

Fundamento da verificação: as páginas `gestor/agenda/page.tsx` e `profissional/agenda/page.tsx` e todos os arquivos de `src/components/agenda/` usados por elas não contêm qualquer referência a disponibilidade ou slots livres; a célula de horário vazia em `CalendarGrid.tsx` é apenas espaço gráfico, sem rótulo nem clique; `BookingDetailModal.tsx` oferece somente ações de status e pagamento; a busca de consumidores não encontrou uso de interface para a função de remarcação `updateBooking` (`src/app/(public)/booking/_lib/bookings.ts:457`), que continua existindo como biblioteca com verificação de conflito (`bookings.ts:470`).

Explicação obrigatória:

A criação de agendamentos e o cálculo de disponibilidade existem no fluxo público do cliente. Essas capacidades não pertencem à tela autenticada da agenda do gestor analisada nesta auditoria.

## 6. Componentes não alcançados pelas rotas consultadas

Em `src/components/agenda/` e `src/hooks/`:

- AgendaView;
- AgendaContainer;
- NewBookingDialog;
- DayView;
- WeekView;
- MonthView;
- BookingBlock;
- TimeSlot;
- useAvailableSlots.

Classificação obrigatória: **"Componentes não alcançados pelas rotas consultadas."**

Registro:

- Não foram considerados capacidades disponíveis na agenda viva.
- Não foram classificados como código morto.
- Remoção ou integração desses componentes está fora do escopo.

Base da verificação: a consulta de consumidores localizou apenas exportações internas (`src/components/agenda/index.ts`, `src/components/lazy/index.tsx`) e um comentário; nenhuma rota autenticada importa esse conjunto. Como a busca foi feita sobre as rotas consultadas, a ausência de consumidor não autoriza concluir que o componente nunca será alcançado — daí a classificação, e não a de código morto.

## 7. Notificações e lembrete de 24 horas

Registro exato:

"O Salao02 contém implementação técnica de notificações e lembrete de 24 horas, acompanhada por testes unitários aprovados durante a auditoria. A auditoria não comprovou implantação ativa do scheduler, configuração vigente dos provedores nem entrega real por e-mail, SMS, WhatsApp ou push. Por isso, essas capacidades permanecem indisponíveis para promessa comercial na campanha NS-001."

Classificação:

| Item | Classificação |
| --- | --- |
| Implementação técnica | confirmada no código |
| Comportamento isolado | confirmado por testes unitários |
| Scheduler implantado | pendente |
| Chaves internas configuradas | pendente |
| Provedores configurados | pendente |
| Entrega real | pendente |
| Promessa comercial | não autorizada |
| Demonstração na NS-001 | não autorizada |

A operação pode depender de:

- rota interna de reminder — `src/app/api/internal/booking-reminders/24h/route.ts`;
- scheduler — `functions/src/index.ts:959`, `sendBookingReminders24h` com `.schedule("every 60 minutes")`;
- chaves internas — nomes em `docs/environments.md:70`, sem valores;
- URL da aplicação — mesma linha da documentação de ambientes;
- provedor de e-mail — nomes de variáveis, sem valores;
- provedores opcionais de SMS e WhatsApp — nomes de variáveis, sem valores.

Não registrar valores de variáveis.

Contexto que sustenta a classificação: `docs/features.md:69` lista "Reminder automatico 24h" como função do produto, e a documentação de prontidão mantém SMS e WhatsApp como canais técnicos sem smoke real. Ou seja, o repositório afirma a implementação e, ao mesmo tempo, não registra comprovação de entrega. A campanha NS-001 permanece proibida de usar qualquer uma das duas pontas como mensagem: nem "o sistema não possui lembretes", nem "o sistema envia lembretes".

## 8. Evidências consultadas

Cada linha registra o caminho, a conclusão que a evidência sustenta e o limite dessa conclusão.

| Caminho no Salao02 | Conclusão sustentada | Limite da conclusão |
| --- | --- | --- |
| `src/app/(dashboard)/gestor/agenda/page.tsx` | A tela do gestor lê agendamentos do salão, filtra por profissional, status e nome de cliente, altera status, registra pagamento local e exporta CSV. | Não prova comportamento em navegador nem em produção. |
| `ROUTE_MAP.md` | Existem rotas estáticas `/gestor/agenda` e `/profissional/agenda`. | Mapa de rotas não prova renderização nem autorização real. |
| `src/app/(dashboard)/profissional/agenda/page.tsx` | A agenda do profissional é escopada pelo próprio profissional, aceita `?date=` e oferece bloqueio de horário. | Não é a tela do gestor; nada aqui autoriza promessa sobre a visão do gestor. |
| `src/components/agenda/CalendarGrid.tsx` | Grade com faixa fixa de 08:00 a 20:00 (`:85`-`:86`), ramo mobile (`:152`) e estado vazio (`:171`). | Faixa fixa e classe responsiva não provam adequação a expediente real nem uso em celular. |
| `src/components/agenda/BookingCard.tsx` | Status e rótulos visíveis; em modo compacto o nome do cliente não aparece. | Não prova legibilidade em tela pequena. |
| `src/components/agenda/BookingDetailModal.tsx` | Mostra horário, cliente, profissional, serviço, preço e status; oferece ações de status e pagamento local. | Ausência de edição confirmada nesta tela; não testada em navegador. |
| `src/components/agenda/DayNavigator.tsx` | Navegação por período e botão "Hoje". | Não prova o efeito da navegação sobre os dados. |
| `src/components/agenda/AgendaViewSwitcher.tsx` | Alternância entre Dia, Semana e Mês. | Comportamento sustentado por teste jsdom, não pela tela publicada. |
| `src/app/(public)/booking/_lib/bookings.ts` | Criação, bloqueio e mudança de status com verificação de conflito (`:264`); `updateBooking` (`:457`) também verifica conflito (`:470`). | Biblioteca, sem interface que a use para remarcar. |
| `src/app/api/public/availability/route.ts` | Cálculo de slots disponível, com horário efetivo, pausas, feriados e antecedência mínima. | Superfície pública do cliente; não pertence à agenda do gestor. |
| `src/app/api/public/availability/availability-helpers.ts` | Regras do cálculo de disponibilidade. | Idem. |
| `src/app/(public)/booking/_components/DateTimeSelection.tsx` | Único ponto da aplicação que exibe horários livres para o cliente. | Não autoriza afirmar disponibilidade na tela do gestor. |
| `functions/src/index.ts` (`:959`) | Definição de scheduler de lembrete a cada 60 minutos. | Definir a função não prova implantação no projeto publicado. |
| `src/lib/notifications/booking-reminders.ts` | Lógica de janela, preferências, reivindicação idempotente e envio. | Executada com mocks; não comprova entrega. |
| `src/app/api/internal/booking-reminders/24h/route.ts` | Rota interna protegida por chave. | Chave real não verificada. |
| `src/lib/notifications/notifications-server.ts` | Notificação in-app sempre; canais externos condicionais. | Provedores e produção não fumados. |
| `firestore.rules` (`:212`) | Política de leitura, escrita e exclusão por papel no tenant. | Regra escrita não prova implantação no ambiente publicado. |
| `src/middleware.ts` | Gate de papel para rotas `/gestor`. | Gate de rota não substitui teste autenticado. |
| `docs/features.md` (`:69`) | O reminder de 24h consta como função do produto. | Documentação não prova funcionamento. |
| `docs/environments.md` (`:70`) | Nomes das variáveis de jobs internos. | Nomes sem valores; configuração real desconhecida. |
| `docs/contexto/HANDOFF.md` | Registro de releases, gates e da ausência de contas de teste (`:72`). | Histórico do projeto, não evidência desta campanha. |
| `docs/runbooks/local-full-user-journey-e2e.md` | Existe jornada E2E local com emuladores, Chromium e worker único. | Runbook não executado nesta validação. |
| `src/components/agenda/AgendaViewSwitcher.test.tsx` | Teste comportamental de troca de visão. | jsdom com componente isolado. |
| `src/app/(dashboard)/gestor/agenda/page.test.ts` | Asserção sobre o texto-fonte da página. | Não exerce comportamento. |
| `src/components/agenda/BookingDetailModal.test.ts` | Asserção sobre o texto-fonte do modal. | Não exerce comportamento. |
| `src/app/(public)/booking/_lib/__tests__/bookings.test.ts` | Criação, pagamento pendente, cancelamento, conclusão e espera de pagamento. | Ramo de conflito não coberto; `fetch` com mock fixo. |
| `src/app/api/bookings/cancel/route.test.ts` | Cancelamento, waitlist e recusa entre tenants. | Mocks, sem ambiente publicado. |
| `src/lib/notifications/booking-reminders.test.ts` | Elegibilidade, preferência, idempotência e falha do reminder. | `sendNotification` mockado. |
| `src/app/api/internal/booking-reminders/24h/route.test.ts` | Bloqueio sem chave e execução com chave. | Chave de teste, não a real. |
| `e2e/tests/agenda.spec.ts` | Cobertura prevista da tela do gestor. | Gateado por credenciais de E2E; não executado. |
| `e2e/tests/profissional/agenda.spec.ts` | Cobertura prevista da tela do profissional. | Pulado por decisão registrada no próprio arquivo. |
| `e2e/tests/local/full-user-journey.spec.ts` | Criar agendamento e conferi-lo na agenda do gestor. | Exige emuladores; não executado. |

Caminhos citados sem número de linha foram conferidos por arquivo; quando um caminho específico não puder ser reconfirmado em tarefa futura, registrar "Caminho completo pendente de conferência no repositório Salao02." em vez de presumir.

## 9. Decisão editorial

### Liberado pelas evidências atuais

- Mostrar agendamentos ocupados.
- Mostrar as visões dia, semana e mês.
- Mostrar filtros por profissional.
- Mostrar filtros por status.
- Mostrar busca por cliente.
- Abrir detalhes.
- Mostrar horário.
- Mostrar cliente fictício.
- Mostrar profissional fictício.
- Mostrar serviço fictício.
- Mostrar preço fictício.
- Mostrar status.
- Mostrar alteração de status.
- Mostrar confirmação.
- Mostrar cancelamento.
- Mostrar conclusão.
- Mostrar no-show.
- Mostrar pagamento local.
- Mostrar exportação CSV somente com dados fictícios.

Nenhum destes itens libera gravação. Liberar significa apenas que a afirmação tem sustentação no código e pode ser demonstrada depois da execução autenticada local, em ambiente com emuladores e dados fictícios.

### Liberado com ajuste

- "Tenha mais clareza sobre os agendamentos do seu salão."
- "Acompanhe os agendamentos do dia, da semana ou do mês."
- "Visualize a rotina de atendimentos de forma organizada."
- "Consulte os agendamentos por profissional e status."
- "Conheça a agenda do Marca Salão."

Ajuste comum: formulação sobre visualização e acompanhamento, nunca sobre descoberta de vagas, resultado comercial ou automação.

### Bloqueado

- Horários disponíveis na agenda do gestor.
- Slots livres na agenda do gestor.
- Criação pela agenda do gestor.
- Edição.
- Remarcação.
- Exclusão.
- Duração como campo próprio.
- Prevenção automática de no-show.
- Preenchimento automático.
- Mensagens como promessa comercial.
- Reminder de 24 horas como promessa comercial.
- Confirmação automática.
- Ocupação garantida.
- Agenda sempre cheia.
- Aumento garantido de faturamento.
- Redução garantida de faltas.

## 10. Riscos para gravação

- Exposição de dados pessoais.
- Nomes reais.
- Telefones.
- E-mails.
- Observações.
- Identificadores internos.
- Dados de profissionais reais.
- Dados de serviços reais.
- Preço real.
- Exportação CSV com dados reais.
- Uso de captura desatualizada.
- Demonstração de comportamento não validado.
- Gravação com console ou ferramentas de desenvolvimento abertas.
- Uso de ambiente remoto por engano.

Mitigações:

- Usar somente emuladores.
- Usar somente dados fictícios.
- Revisar cada quadro.
- Não abrir exportação em ambiente real.
- Não usar credencial antiga.
- Não gravar staging ou produção sem autorização independente.
- Manter gravação bloqueada até o E2E local.

## 11. Jornada E2E local recomendada

O projeto possui o runbook:

docs/runbooks/local-full-user-journey-e2e.md

A jornada deve:

- Usar Firebase Auth Emulator.
- Usar Firestore Emulator.
- Usar pagamento mock.
- Usar autenticação simulada.
- Criar perfis fictícios.
- Criar agendamento pelo fluxo público.
- Verificar o agendamento para cliente, gestor e profissional.
- Executar em Chromium.
- Usar um worker.
- Não chamar Stripe real.
- Não escrever em produção.

Não executar os comandos nesta tarefa. Não copiar valores de credenciais. Registrar como próxima validação independente.

Valor desta jornada para a NS-001: ela é o caminho que transforma a coluna "autenticado" da seção 4 de pendente em confirmado, produz ao mesmo tempo a evidência de integração entre o agendamento público e a agenda do gestor e gera a captura atualizada que a campanha hoje não tem.

## 12. Pendências

- Executar o E2E local com emuladores.
- Registrar o resultado do provisionamento.
- Confirmar o agendamento criado pelo cliente na agenda do gestor.
- Confirmar as visões dia, semana e mês no navegador.
- Confirmar filtros por profissional.
- Confirmar filtros por status.
- Confirmar busca por cliente.
- Confirmar modal de detalhes.
- Confirmar ações de status.
- Validar comportamento móvel.
- Validar a captura atual.
- Substituir dados por informações fictícias.
- Verificar se o horário fixo 08:00–20:00 representa corretamente a interface.
- Verificar o deep link com parâmetro client.
- Confirmar implantação do scheduler.
- Confirmar configuração dos provedores.
- Confirmar entrega real dos canais.
- Revisar o reminder em campanha separada.
- Trocar a senha da conta demo no sistema real, se ainda estiver pendente.
- Tratar histórico Git da credencial em tarefa separada, caso aprovado.

## 13. Aprovação

- Elaborado por: pendente de definição
- Revisado por: pendente
- Aprovado por: pendente
- Data da aprovação: pendente
- Uso para gravação: não autorizado
- Uso para publicação: não autorizado
- Observações: validação baseada em leitura de código e testes selecionados; execução autenticada ainda pendente.
