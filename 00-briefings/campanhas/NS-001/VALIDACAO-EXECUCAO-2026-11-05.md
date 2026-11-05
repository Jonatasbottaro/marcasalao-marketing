# Validação por execução autenticada — agenda do gestor (NS-001)

- Data da execução: 2026-11-05, entre 10:11 e 10:41 (America/Sao_Paulo; logs do app em UTC 13:11–13:41)
- Executada por: assistente de marketing do Marca Salão (agente), sob solicitação do titular para destravar a NS-001
- Ambiente: estação Windows local (checkout `D:\MEGA\Antigravity\Salao02`), Firebase Emulator (auth em `localhost:9099`, firestore em `localhost:8080`), aplicação local em `http://localhost:5100` via `next start`, Chromium do Playwright 1.58.2, viewport móvel emulado 390 × 844
- Runbook seguido: `docs/runbooks/local-full-user-journey-e2e.md` do repositório Salao02
- Estado do código: a execução ocorreu sobre o conteúdo presente no checkout local. Como o diretório executado não possuía metadados Git verificáveis, a execução comprova comportamento do ambiente local observado, mas não estabelece por si só identidade exata com um commit remoto. A referência técnica da campanha continua sendo o commit `6342a33a36b0a4eadd0f5a62770f1eee485156ee` auditado em [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md); esta execução não substitui aquela auditoria.
- Dados: integralmente fictícios (namespace `e2e-1793884270981`; salão "Meu Salão E2E"; pessoas fictícias Ana Souza, Bruno Lima, Maria Oliveira, João Pereira, Carla Santos, Pedro Costa, Lucia Ferreira). Nenhum dado real de cliente foi usado. Nenhuma credencial, senha, token, cookie ou sessão é registrada neste documento; o login usou o gestor fictício da execução namespaced, cujo identificador completo permanece apenas no ambiente local de teste.

## 1. Execução da jornada E2E automatizada

Comandos, na ordem do runbook:

1. `npm run firebase -- emulators:start --only auth,firestore --project salao02-v2`
2. `npm run e2e:provision`
3. `npm run test:e2e:local:journey`

Resultado: **1 passed (1.5m)** — jornada serial completa de gestor, profissional e cliente: criação de conta e onboarding do gestor, criação e edição de serviço, vínculo e aprovação de profissional, cadastro de cliente, agendamento pelo fluxo público com pagamento mock, agendamento visível para cliente, gestor e profissional, conclusão e avaliação.

Ajustes de ambiente feitos nesta estação, sem alterar código da aplicação: instalação do Eclipse Temurin JRE 21 (exigência do emulador Firestore), restauração de `node_modules` corrompido pelo sync do MEGA (`npm install`) e criação de `.env.local` apenas com valores públicos de emulador (projeto `salao02-v2`, chave web pública já exposta como fallback em `src/lib/firebase/config.ts`, `NEXT_PUBLIC_FIREBASE_EMULATOR=true`, pagamentos mock). Nenhum arquivo `.env` de segredos foi lido ou versionado.

## 2. Verificação manual autenticada no navegador

Sessão autenticada como gestor fictício da execução namespaced, em `http://localhost:5100/gestor/agenda`. Observado na interface:

- aplicação local iniciada e autenticação do gestor efetivada;
- rota `/gestor/agenda` renderizada com cabeçalho "Agenda do salão" e subtítulo "Acompanhe os atendimentos por período, profissional e status.";
- carregamento dos dados da agenda;
- visão **Dia**: grade 08:00–20:00 com o agendamento do período;
- visão **Semana**: sete colunas (02/11–08/11) com os agendamentos distribuídos por dia;
- visão **Mês**: grade de novembro/2026 com chips de agendamento nos dias 02, 03, 04, 05, 08 e 09;
- navegação por data e botão "Hoje";
- **filtro por profissional**: lista carregada com os profissionais aprovados do salão; ao selecionar um, a semana passou a exibir somente os agendamentos dele;
- **filtro por status**: opções Pendente, Confirmado, Concluído, Cancelado e No-show; ao selecionar "Cancelado" restou somente o agendamento cancelado;
- **busca por nome de cliente**: com debounce; ao digitar um nome fictício restou somente o agendamento daquela pessoa;
- **modal de detalhes**: horário, cliente, profissional, serviço, preço, status e status de pagamento; sem campos de edição, remarcação ou exclusão e sem duração como campo próprio — coerente com a auditoria de código;
- **ação manual Confirmar**: executada sobre o agendamento pendente do dia; o cartão passou de "Pendente" para "Confirmado" e o estado persistiu após recarga da página; nenhuma mensagem enviada, nenhuma notificação externa exercitada, nenhuma confirmação automática;
- **viewport móvel 390 × 844**: layout empilhado e legível; na visão semana os agendamentos viram cartões com horário, serviço, cliente e badges de status/pagamento;
- jornada pública integrada à agenda: o agendamento criado pelo fluxo público do cliente apareceu na agenda do gestor (coberto pela jornada E2E);
- dados fictícios em toda a sessão.

## 3. Limites expressos desta execução

- Execução realizada somente em emuladores locais; **produção não acessada** e staging não acessado.
- **Aparelho físico real não testado**; a verificação móvel foi por emulação de viewport em Chromium.
- **Conteúdo gerado por "Exportar CSV" não foi exportado** nem inspecionado (regra de proteção de dados da campanha).
- **Notificações externas não exercitadas**: e-mail, SMS, WhatsApp e push permanecem sem validação de entrega; scheduler em produção não foi confirmado.
- **Gravação e publicação não autorizadas** por esta execução; nenhuma peça, legenda, narração, áudio ou composição foi criada.

## 4. Anomalias da massa de teste (limitações da fixture, não defeitos comprovados da agenda)

1. Alguns agendamentos do seed não possuíam `clientName` denormalizado. Consequência: apareciam como "Cliente não identificado" quando a leitura complementar do usuário era bloqueada pelas regras de segurança.
2. Profissionais do seed não possuíam campo `name`. Consequência: a consulta ordenada por `name` não retornava esses documentos e o filtro por profissional ficou vazio até o enriquecimento local da massa fictícia.
3. O seed possuía preço fictício de R$ 12.000,00. Consequência: válido para teste técnico, inadequado para material publicitário.

O enriquecimento foi realizado somente no Firestore Emulator, por script admin descartável; nenhuma alteração correspondente foi feita no produto.

Recomendação futura registrada: "Criar uma fixture editorial separada, com nomes fictícios neutros, campos completos, serviços e valores plausíveis, para obtenção de capturas e gravações finais." Essa fixture não foi criada nesta tarefa.

## 5. Capturas de evidência e suas limitações

Pasta [`capturas/2026-11-05/`](capturas/2026-11-05/), 12 arquivos, todos com dados fictícios:

| Arquivo | Conteúdo |
| --- | --- |
| `01-agenda-visao-dia.png` | Visão dia desktop, agendamento pendente do dia |
| `02-agenda-modal-detalhes.png` | Modal de detalhes antes da confirmação (status Pendente) |
| `03-agenda-status-confirmado.png` | Visão dia após a ação Confirmar na UI |
| `04-agenda-visao-semana.png` | Visão semana desktop com os agendamentos da semana |
| `05-agenda-visao-mes.png` | Visão mês desktop (novembro/2026) |
| `06-agenda-filtro-status-cancelado.png` | Filtro de status "Cancelado" aplicado |
| `07-agenda-filtro-profissional.png` | Filtro por profissional aplicado na semana |
| `08-agenda-busca-cliente.png` | Busca por nome de cliente aplicada |
| `09-agenda-modal-confirmado.png` | Modal com cliente/profissional nomeados e status Confirmado |
| `10-agenda-mobile-dia.png` | Visão dia em viewport 390×844 |
| `11-agenda-mobile-semana.png` | Visão semana mobile, topo |
| `12-agenda-mobile-semana-grade.png` | Visão semana mobile, cartões de agendamento |

As capturas de 2026-11-05 passam a ser a evidência técnica mais recente da campanha. A captura anterior permanece como histórico.

**As capturas de 2026-11-05 são evidência técnica. Não estão automaticamente aprovadas como frames de publicação.** Motivos:

- identificação técnica E2E visível ("Meu Salão E2E e2e-1793884270981", "Gestor E2E");
- enquadramento de validação, com scrollbar e menu administrativo amplo;
- possíveis valores fictícios inadequados (preço de R$ 12.000,00);
- necessidade de adaptação ao formato vertical da narrativa;
- necessidade de revisão de marca;
- necessidade de fixture editorial dedicada;
- necessidade de revisão quadro a quadro antes de qualquer uso público.

A captura da visão Dia comprova visualmente: menu lateral, área da agenda, cabeçalho "AGENDA DO SALÃO", texto "Acompanhe os atendimentos por período, profissional e status", navegação de data, seletor Dia/Semana/Mês, campo "Buscar cliente", filtros de profissional e status, grade por horário, agendamento do período, status e status de pagamento, botão "Exportar CSV". Ela não comprova por si só o funcionamento das interações; o funcionamento foi comprovado pela execução autenticada documentada neste arquivo.

Inspecionadas uma a uma nesta consolidação: ausência de telefone, e-mail, credencial, token, cookie e console aberto; somente dados fictícios; nenhuma tela de produção.

## 6. Pendência editorial de marca

A interface capturada exibe o nome de produto "Meu Salão" (sidebar e título da página), enquanto a campanha usa "Marca Salão". A produção final deve confirmar qual nome e identidade visual são oficiais para uso público. Não alterar a interface do produto e não corrigir a captura por edição sem autorização; não afirmar que um dos nomes está errado sem decisão oficial.

## 7. Efeito sobre as pendências da campanha

Resolvidas por esta execução: execução autenticada local com emuladores; confirmação em navegador das visões, da navegação por data, dos filtros, da busca, do modal e da ação de status; validação de legibilidade em viewport móvel emulado; captura atualizada da agenda como evidência técnica mais recente.

Continuam abertas e dependem do titular: aprovação do briefing, do hook e do roteiro; definição de responsável pela campanha; CTA e destino por canal (inclusive link externo do perfil no Instagram); revisão final de textos de tela e narração; estimativa de duração por leitura cronometrada; confirmação do nome de marca para uso público; autorização de gravação e de publicação. Esta validação **não autoriza gravar, publicar ou agendar**.
