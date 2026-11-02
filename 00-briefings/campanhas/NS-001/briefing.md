# Briefing de campanha

> Briefing piloto da Content Factory, preenchido a partir de [`../../TEMPLATE-BRIEFING.md`](../../TEMPLATE-BRIEFING.md). Este documento **não** é roteiro, legenda, arte nem registro de publicação. Ele registra a dor, a evidência disponível e os limites de promessa de uma campanha futura.
>
> Classificação usada em todo o documento: **confirmado** (sustentado por evidência consultada), **hipótese** (plausível, sem comprovação), **pendente de validação** (precisa ser testado antes da produção).

## 1. Identificação

- Código: NS-001
- Nome: Organização e visibilidade da agenda
- Responsável: pendente de definição (não há responsável documentado no repositório)
- Data de criação: 2026-11-02
- Data de atualização: 2026-11-02
- Status: em validação
- Versão: 0.1

## 2. Objetivo da campanha

- Objetivo principal: apresentar como uma agenda organizada ajuda o salão a visualizar atendimentos e horários disponíveis, usando o Marca Salão como demonstração concreta somente nos comportamentos validados.
- Resultado esperado: gerar interesse em conhecer a agenda do Marca Salão e solicitar uma demonstração.
- Canal ou canais: proposta inicial — Instagram Stories, Instagram Reels, YouTube Shorts, TikTok; WhatsApp Status se compatível com a estratégia já documentada. Nenhum canal foi publicado; nada aqui registra publicação realizada.
- Formato ou formatos: proposta — peça vertical com captura real da agenda e narração em texto separado, conforme [`../../../WORKFLOW.md`](../../../WORKFLOW.md). Definição final pendente de roteiro e edição.

Não prometer: redução de faltas, aumento de faturamento, aumento de ocupação, preenchimento de horários, resultado operacional garantido.

## 3. Público

- Público principal: pessoas responsáveis pela gestão de salões de beleza.
- Segmento: pequenos negócios do setor de beleza que ainda controlam horários de forma manual ou fragmentada; responsáveis pela organização da agenda e dos atendimentos.
- Contexto de uso: acompanhamento dos atendimentos marcados e identificação de espaços disponíveis durante o dia ou a semana.
- Nível de conhecimento sobre o Marca Salão: não documentado — tratar como hipótese.

Não há no repositório pesquisa, censo ou dado sobre o público. Idade, renda, quantidade de salões, número de usuários e comportamento de compra **não** foram levantados e não devem ser afirmados na campanha sem fonte.

## 4. Dor principal

- Dor: falta de clareza sobre a ocupação da agenda e existência de horários vazios.
- Situação em que ocorre: a gestão precisa acompanhar atendimentos marcados e identificar espaços disponíveis durante o dia ou a semana.
- Como o público descreveria essa dor: "Você sabe quais horários ainda estão disponíveis no seu salão?" — formulação permitida como pergunta de reconhecimento. Não afirmar que todos os salões possuem esse problema.
- Frequência ou recorrência: não medida.
- Evidência disponível: nenhuma pesquisa quantitativa localizada no material consultado ([`../../../docs/historico/2026-11-02-apresentacao-sistema-salao02.md`](../../../docs/historico/2026-11-02-apresentacao-sistema-salao02.md), [`../../../04-legendas/`](../../../04-legendas/), [`../../../marcas/marcasalao/posts/`](../../../marcas/marcasalao/posts/)).
- Hipóteses ainda não validadas: que horários vazios representem oportunidade de atendimento não aproveitada; que a falta de visibilidade da agenda aumente o esforço de gestão; que o salão perceba isso como problema próprio.

> Não foi localizada, no material consultado, uma pesquisa quantitativa que comprove frequência, volume ou impacto financeiro da dor.

## 5. Impacto

- Impacto operacional: dificuldade de visualizar a distribuição dos atendimentos; maior esforço para acompanhar a agenda; menor clareza sobre espaços disponíveis; dificuldade para planejar a rotina. Descritos como consequências qualitativas da dor, não como medição.
- Impacto financeiro: **hipótese, sem valores.** Um horário sem atendimento pode representar uma oportunidade de receita não realizada, mas o impacto depende do serviço, do preço, da duração, da procura e da possibilidade de reagendamento.
- Impacto na experiência do cliente: não avaliado — pendente.
- Impacto na equipe: não avaliado — pendente.
- Consequência de não agir: a gestão continua dependendo de anotações ou memória para saber o que está ocupado; formulação qualitativa, sem dado.

Não inventar: ticket médio, quantidade de faltas, prejuízo mensal, percentual de ocupação, retorno sobre investimento. Nenhum número aparece neste briefing e nenhum deve aparecer na campanha sem fonte identificável.

## 6. Solução proposta

- Abordagem: centralizar e visualizar os agendamentos em uma agenda do sistema, limitada aos comportamentos efetivamente confirmados na validação.
- Como o Marca Salão participa: oferece uma tela de agenda no painel do salão. O que ela faz de fato está separado em confirmado, hipótese e pendência na seção 7 — a campanha só usa a coluna confirmada, revalidada na data da produção.
- O que depende do estabelecimento: registrar corretamente os agendamentos; manter os dados atualizados; acompanhar os horários; estabelecer o próprio processo de contato com clientes; administrar cancelamentos, confirmações e remarcações pelos meios adotados pelo salão.
- Limitações: **o sistema não envia mensagens, lembretes ou confirmações automáticas.** Não há automação comprovada de contato com cliente nem de prevenção de faltas. Qualquer ação sobre o cliente — avisar, confirmar, remarcar — depende do salão e dos meios que ele usar.
- O que não será prometido: ver seção 8.

## 7. Funcionalidade usada como prova

- Funcionalidade: Agenda do Marca Salão (painel do salão, item de menu "Agendamentos").
- Onde está disponível: no painel do gestor, item de menu "Agendamentos" — visível na captura consultada. A rota exata não foi revalidada neste briefing; a leitura de código arquivada em [`../../../marcas/marcasalao/posts/2026-10-18-organizacao-agenda-equipe/README.md`](../../../marcas/marcasalao/posts/2026-10-18-organizacao-agenda-equipe/README.md) cita `src/app/(dashboard)/gestor/agenda/page.tsx` do repositório `Jonatasbottaro/Salao02`. Revalidar rota e caminho antes de afirmar qualquer endereço na peça.

### Confirmado

Sustentado por evidência consultada, com o alcance real de cada evidência:

- Elementos visíveis na tela, por [`../../../01-insta-stories/05_agenda.png`](../../../01-insta-stories/05_agenda.png) (arquivo registrado no Git em 02/10/2026 pelo commit `a6e7f79` "Substitui imagens por capturas reais do site marcasalao.com.br com conta demo"; a própria tela exibe a data "Sexta, 02 De Out 2026" e o ambiente "Studio Bella – Demonstração"): cabeçalho "AGENDA DO SALÃO"; subtítulo "Acompanhe os atendimentos por período, profissional e status."; controles de navegação de data (anterior, rótulo da data, próximo, "Hoje"); seletor de visão com três rótulos "Dia", "Semana", "Mês"; campo "Buscar cliente"; selects "Todos os profissionais" e "Todos status"; grade de horário com marcador "08:00"; controle "Exportar CSV"; item de menu "Agendamentos" selecionado.
- Existência dos recursos, por leitura de código registrada em 18/10/2026: visões dia, semana e mês; filtro por profissional e status; busca de cliente; detalhes do atendimento com cliente, serviço, profissional e horário. O próprio registro afirma: "A leitura de código confirma a existência dos recursos; não foi realizado teste funcional completo do painel."
- Fluxo público de agendamento, por verificação documentada em [`../../../marcas/marcasalao/posts/2026-10-18-como-funciona-agendamento/README.md`](../../../marcas/marcasalao/posts/2026-10-18-como-funciona-agendamento/README.md): a sequência identificação → serviço → profissional → data/horário → resumo antes da confirmação foi confirmada no código `src/app/(public)/booking/_components/BookingWizard.tsx` e na entrada pública `https://marcasalao.com.br/booking/demo-studio-bella`. Isso comprova o fluxo do cliente, **não** o comportamento da agenda do gestor.

Nenhum item acima comprova que os controles funcionam, que a tela está atualizada em 2026-11-02, nem que existe integração entre o agendamento público e a agenda do painel.

### Hipótese

Sugeridas pela interface, ainda sem comprovação:

- A faixa vazia sob "08:00" representa horário sem atendimento.
- Os filtros de profissional e status alteram a listagem exibida.
- A busca por cliente localiza atendimentos na agenda.
- As visões "Semana" e "Mês" apresentam a mesma informação em outra granularidade.
- "Exportar CSV" gera um arquivo com os dados do período exibido.
- O selo numérico no ícone de notificação do cabeçalho se relaciona com atendimentos pendentes.
- Os dados do ambiente "Studio Bella – Demonstração" são fictícios.

### Pendente de validação

Testar antes de qualquer produção; nenhum destes foi confirmado:

- Criar agendamento pelo painel do salão.
- Editar agendamento existente.
- Cancelar agendamento e o que a tela mostra depois disso.
- Alterar horário de um atendimento.
- Exibir horários disponíveis de forma explícita para a gestão.
- Associação entre cliente, profissional e serviço na tela do gestor.
- Valores possíveis do filtro de status e o que cada um significa.
- Prevenção de conflito de horário no mesmo profissional.
- Comportamento em celular.
- Estado atual da tela: a captura mais recente registrada no repositório é de 02/10/2026; revalidar antes de usar.

- Evidência da verificação: capture de tela nova, datada, com rota e ambiente identificados; teste funcional registrado com responsável e data.
- Captura ou demonstração necessária: captura atual da agenda; gravação de tela somente após validar o fluxo escolhido.
- Responsável pela validação: pendente de definição.
- Data da validação: não realizada.

> ⚠️ **Atenção:** o Marca Salão não possui mensagens, lembretes ou confirmações automáticas. A campanha NS-001 não pode atribuir essas capacidades ao produto.

Uma captura de tela comprova apenas o que está visível nela. Ela não comprova que um botão funciona, que um filtro filtra, que uma exportação exporta, nem que a agenda do painel reflete os agendamentos feitos pela página pública.

## 8. Mensagem

- Mensagem principal: "Tenha mais clareza sobre os horários ocupados e disponíveis do seu salão." Só poderá ser usada na produção se a visualização correspondente estiver validada na tela real.
- Promessa permitida: "Organize e visualize sua agenda em um só lugar." Usar somente se a centralização da agenda tiver sido confirmada em validação registrada.
- Afirmações que precisam de comprovação antes de uso: "veja todos os horários disponíveis"; "controle toda a agenda"; "evite conflitos de horário"; "reduza faltas"; "melhore o faturamento"; "aumente a ocupação".
- Palavras ou expressões recomendadas: organizar, visualizar, acompanhar, clareza, rotina, agenda do salão — sempre ligadas a comportamento confirmado.
- Palavras ou expressões proibidas: automático; lembrete automático; confirmação automática; fim das faltas; zero no-show; faturamento garantido; agenda sempre cheia; nunca mais perca clientes; elimine horários vagos; "o Marca Salão reduz suas faltas"; "Nunca mais tenha clientes faltando"; "Envie lembretes automáticos"; "Confirme clientes automaticamente"; "Acabe com o no-show"; "Preencha automaticamente os horários vagos".
- Objeções do público: não levantadas com clientes — registrar como pendência de escuta real. Hipóteses de objeção (mudança de rotina, custo, medo de perder o controle do contato com o cliente) não podem virar texto de campanha sem validação.
- Respostas às objeções: dependem da validação acima; nenhuma resposta está aprovada nesta versão.

## 9. Estrutura do conteúdo

Proposta inicial, ainda não tratada como roteiro aprovado. O roteiro final será criado em outra etapa, depois da validação da seção 7.

- Hook: "Você sabe quais horários ainda estão disponíveis no seu salão?"
- Problema: falta de clareza sobre a ocupação da agenda.
- Consequência: maior dificuldade para acompanhar a rotina e identificar espaços disponíveis.
- Solução: organizar os agendamentos em uma visão centralizada, se essa capacidade estiver validada.
- Demonstração: mostrar somente ações confirmadas na tela real da agenda.
- Resultado esperado: mais clareza e organização operacional, sem garantia de redução de faltas ou aumento de receita.
- CTA: "Conheça a agenda do Marca Salão."

## 10. Materiais necessários

- Captura atual da agenda, revalidada na data da produção (a registrada no Git em 02/10/2026 é a única disponível).
- Validação da resolução e da legibilidade da captura no formato final do canal.
- Gravação de tela somente após validar o fluxo que será demonstrado.
- Elementos oficiais de marca existentes no repositório: identidade verde-petróleo, menta e branco, logo MS/tesoura, conforme as artes aprovadas em [`../../../marcas/marcasalao/posts/`](../../../marcas/marcasalao/posts/).
- Relação das telas adicionais necessárias: pendente da definição do fluxo validado.
- Fonte de qualquer dado que venha a ser utilizado: obrigatória; sem fonte, o dado não entra na peça.
- Proteção ou ocultação de dados pessoais em toda captura, ainda que em ambiente de demonstração.
- Narração em texto separado por cenas e tempos, legendas visíveis e `.srt` sincronizado; vídeo entregue sem áudio, conforme [`../../../WORKFLOW.md`](../../../WORKFLOW.md).

Não incluir captura com: dados reais de clientes, telefone, e-mail, informações pessoais, credenciais, dados sensíveis do estabelecimento. O acesso ao painel de demonstração não fica neste repositório; credenciais não entram em briefing, roteiro, captura ou legenda.

## 11. Canais e adaptações

Proposta inicial, não material publicado. Duração final pendente de roteiro e edição; não definir duração universal sem evidência.

### Canal 1

- Canal: Instagram (Stories e Reels)
- Formato: vertical
- Proporção: padrão do repositório para peças verticais — conferir antes de fixar
- Duração: pendente de roteiro
- Tom: direto e educativo, sem jargão técnico
- CTA: "Conheça a agenda do Marca Salão." + orientação de link na bio, somente se o link externo do perfil estiver confirmado na data da publicação
- Adaptações necessárias: legenda própria; URL não é clicável em legenda do Instagram; botão desenhado em imagem não gera adesivo de link

### Canal 2

- Canal: YouTube Shorts e TikTok
- Formato: vertical
- Proporção: pendente de confirmação por canal
- Duração: pendente de roteiro
- Tom: idem
- CTA: idem, ajustado ao que cada canal permite
- Adaptações necessárias: verificar política de link e formato vigente antes de produzir

### Canal 3

- Canal: WhatsApp Status — apenas se compatível com a estratégia já documentada
- Formato, proporção, duração, tom e CTA: pendentes de definição

Facebook: se entrar na campanha, usar URL completa na legenda com a chamada padrão do projeto; registrar aqui antes de produzir.

## 12. CTA

- CTA principal: "Conheça a agenda do Marca Salão."
- Destino: [`https://marcasalao.com.br`](https://marcasalao.com.br) — endereço oficial documentado e aprovado no repositório. O painel de demonstração (`https://marcasalao.com.br/gestor`) também está documentado, mas exige credenciais que não ficam neste repositório: não prometer acesso direto sem combinar o acesso com o responsável pelo projeto.
- Ação esperada: acessar a apresentação do sistema ou solicitar uma demonstração.
- Como será rastreado: pendente — não há mecanismo de rastreamento definido no repositório. Sem mecanismo definido, registrar como não rastreado, não como "sem resultado".

## 13. Métricas

Métricas pretendidas, sem meta numérica: visualizações, alcance, retenção, cliques, solicitações de demonstração, conversões quando houver definição válida.

- Objetivo de medição: entender se a peça gera interesse em conhecer a agenda.
- Visualizações / alcance / retenção / cliques / solicitações de demonstração / conversões: linha de base ainda não disponível.
- Período de medição: pendente de definição junto com o canal.
- Fonte dos dados: pendente — depende do rastreamento da seção 12.

Nenhuma meta numérica foi criada. Nenhuma métrica realizada foi preenchida: não há publicação desta campanha.

## 14. Riscos e restrições

- Riscos de mensagem: confundir organização da agenda com prevenção automática de faltas; usar o termo no-show como se o sistema resolvesse a causa sozinho; apresentar hipótese como fato; prometer resultado financeiro.
- Riscos de promessa indevida: atribuir mensagens, lembretes ou confirmações automáticas ao sistema; sugerir preenchimento automático de horários vagos; garantir aumento de ocupação ou de faturamento.
- Dependências: validação funcional da agenda antes da produção; captura atualizada; definição de responsável; política de CTA por rede já registrada em [`../../../AGENTS.md`](../../../AGENTS.md).
- Restrições técnicas: vídeo sem áudio, com legendas queimadas e `.srt` correspondente; narração entregue como texto separado.
- Restrições de marca: identidade verde-petróleo, menta e branco; sem tela fictícia; sem simular botão clicável em imagem estática; não republicar para corrigir legenda.
- Risco de material herdado: existem textos antigos neste repositório com linguagem de automação que **não** representa o produto — por exemplo [`../../../04-legendas/roteiro_enviar_link.md`](../../../04-legendas/roteiro_enviar_link.md) ("sua agenda atualiza no automático 24 horas por dia") e [`../../../templates/youtube_horizontal/index.html`](../../../templates/youtube_horizontal/index.html) ("Automatize o envio de lembretes aos clientes"). São rascunhos/template históricos, não referência de qualidade; não devem ser reutilizados nesta campanha. Nenhum foi alterado nesta tarefa.
- Pendências: ver seções 7, 8, 12 e 16.

## 15. Checklist de validação

- [ ] A dor é real e compreensível.
- [x] O público está definido.
- [x] O impacto não foi inventado.
- [ ] A funcionalidade existe no sistema atual.
- [ ] A funcionalidade foi verificada.
- [ ] As capturas correspondem ao comportamento descrito.
- [x] O conteúdo não promete mensagens automáticas.
- [x] O conteúdo não promete lembretes automáticos.
- [x] O conteúdo não promete resultados garantidos.
- [x] A responsabilidade do estabelecimento está clara quando aplicável.
- [x] O CTA está definido.
- [ ] As métricas estão definidas.
- [ ] As pendências críticas foram resolvidas.
- [ ] O briefing foi aprovado antes da produção.
- [ ] A demonstração mostra somente comportamentos confirmados.
- [ ] Nenhum dado pessoal aparece nas capturas.
- [ ] A mensagem não apresenta organização da agenda como prevenção automática de faltas.

Itens marcados referem-se ao texto deste briefing. Itens sobre funcionalidade, captura e métricas permanecem abertos porque a validação ainda não foi feita e a única captura disponível no repositório é a registrada em 02/10/2026.

## 16. Aprovação

- Elaborado por: assistente de marketing do Marca Salão, a partir de [`../../TEMPLATE-BRIEFING.md`](../../TEMPLATE-BRIEFING.md), sob solicitação do titular em 2026-11-02
- Revisado por: pendente de definição
- Aprovado por: pendente
- Data da aprovação: pendente
- Observações: briefing em validação; produção não autorizada até a validação funcional da agenda. Este documento não autoriza publicar, agendar ou gerar materiais. Estados e critério de pronto em [`../../README.md`](../../README.md).
