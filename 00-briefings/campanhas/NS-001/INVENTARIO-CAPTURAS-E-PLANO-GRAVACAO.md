# Inventário de capturas e plano de gravação — NS-001 (24/11/2026)

Natureza: inventário + plano. **Nenhuma gravação foi executada nesta rodada.** As capturas existentes são evidência técnica, não frames publicitários aprovados.

## 1. Inventário classificado — `capturas/2026-11-05/` (12 arquivos)

Dimensões conferidas por leitura de header PNG: desktop 1440×900 (16:10); mobile 390×844. **Nenhum arquivo está em 9:16** — adaptação vertical obrigatória para uso em Reels/Shorts.

| Arquivo | Dimensão | Classificação | Uso proposto |
| --- | --- | --- | --- |
| 01-agenda-visao-dia.png | 1440×900 | Evidência técnica + referência visual de enquadramento | Referência da cena 3 (visão Dia); não usar como frame final |
| 02-agenda-modal-detalhes.png | 1440×900 | Evidência técnica | Referência da cena 5 (modal Pendente) |
| 03-agenda-status-confirmado.png | 1440×900 | Evidência técnica | Referência da cena 6 (pós-Confirmar) |
| 04-agenda-visao-semana.png | 1440×900 | Evidência técnica | Referência da cena 3 (Semana) |
| 05-agenda-visao-mes.png | 1440×900 | Evidência técnica | Referência da cena 3 (Mês) |
| 06-agenda-filtro-status-cancelado.png | 1440×900 | Evidência técnica | Referência da cena 4 (filtro status) |
| 07-agenda-filtro-profissional.png | 1440×900 | Evidência técnica | Referência da cena 4 (filtro profissional) |
| 08-agenda-busca-cliente.png | 1440×900 | Evidência técnica | Referência da cena 4 (busca) |
| 09-agenda-modal-confirmado.png | 1440×900 | Evidência técnica | Referência das cenas 5/6 (modal Confirmado) |
| 10-agenda-mobile-dia.png | 390×844 | Evidência técnica + referência visual de layout móvel | Referência de legibilidade da cena 3 |
| 11-agenda-mobile-semana.png | 390×844 | Evidência técnica | Referência de layout móvel (topo) |
| 12-agenda-mobile-semana-grade.png | 390×844 | Evidência técnica | Referência de cartões móveis |

Classificações adicionais aplicadas ao conjunto:
- **Captura histórica:** a captura de 02/10/2026 (`01-insta-stories/05_agenda.png`, commit `a6e7f79`) permanece só como histórico.
- **Fixture de teste:** a massa E2E (`e2e-1793884270981`, "Meu Salão E2E", preço R$ 12.000,00) é fixture técnica; continua identificada como fixture.
- **Material descartado da proposta:** nenhum arquivo é descartado do acervo (preservação); todos são descartados **como frames finais** pelos motivos abaixo.
- **Captura final pendente:** todas as cenas 3–6 exigem gravação nova com fixture editorial.

### Verificações obrigatórias (resultado sobre o conjunto de 05/11)

| Verificação | Resultado |
| --- | --- |
| Qualidade visual / resolução | PNG nítidos, 1440×900 e 390×844; insuficientes como frame 1080×1920 sem recorte/upscaling |
| Legibilidade | Boa em desktop; mobile legível em 390×844 (execução §2) |
| Proporção | 16:10 e ~0,462 — nenhuma em 9:16; adaptação pendente |
| Enquadramento | Validação técnica: scrollbar e menu administrativo amplos visíveis |
| Informações sensíveis | Ausentes (inspeção uma a uma registrada na execução §5): sem telefone, e-mail, credencial, token, cookie, console |
| Dados reais ou fictícios | Integralmente fictícios |
| Nome na interface | "Meu Salão E2E" / "Gestor E2E" visíveis — impróprio para peça pública |
| Coerência com a marca | Pendente (decisão de identidade/nome) |
| Compatibilidade com o roteiro | Conteúdo corresponde às cenas 3–6; enquadramento não |
| Atualização do produto | Evidência de 05/11; produto sem revalidação posterior (checkout sem Git) |
| Origem/proveniência | Execução autenticada local registrada com data, ambiente e responsável (agente sob solicitação do titular) |
| Valores fictícios | Preço de R$ 12.000,00 inadequado para publicidade (execução §4) |

## 2. Fixture editorial dedicada (pré-requisito, não criada nesta rodada)

- Namespace próprio (ex.: `editorial-ns001-<data>`), salão com nome público decidido pelo titular.
- Pessoas fictícias neutras (nomes comuns sem sobrenomes reais identificáveis), `clientName` denormalizado e `name` de profissional preenchidos (corrige anomalias 1 e 2 da execução §4).
- Serviços e preços plausíveis (faixa R$ 40,00–R$ 180,00), horários dentro da faixa 08:00–20:00 da grade.
- Estados: ao menos 1 Pendente (para a cena 6), 1 Confirmado, 1 Concluído, 1 Cancelado (para o filtro da cena 4); distribuição em dia/semana/mês coerente com as visões.
- Criação somente no Firestore Emulator, por script descartável; **nenhuma alteração no produto**.

## 3. Plano de gravação (executar somente após aprovações)

Pré-requisitos: briefing + hook + roteiro + plano de captura aprovados; identidade/nome decididos; nova execução autenticada de conferência do produto (runbook `docs/runbooks/local-full-user-journey-e2e.md` do Salao02) sobre a fixture editorial.

Ambiente comum: emuladores Firebase (auth+firestore), app local, Chromium com emulação **450×800 CSS px @ deviceScaleFactor 2,4 → 1080×1920** (ramo móvel da interface, proporção 9:16 exata); gravação de tela ou sequência de frames; sem console/devtools; sem produção/staging.

| Cena | Tela a abrir | Estado inicial | Sequência de interação | Resultado visível esperado | Formato/corte | Riscos | Critério de aceite |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | `/gestor/agenda` visão Dia | Fixture com agendamentos no dia/semana/mês | Clicar seletor Semana → Mês → voltar Dia; navegar data e "Hoje" | Três granularidades do mesmo registro; chips/cartões legíveis | 9:16 nativo da emulação; recorte exclui sidebar | Produto mudou desde 05/11; faixa fixa 08:00–20:00 | Visões conferidas contra matriz A1–A3; sem slots livres; texto legível a 1080×1920 |
| 4 | Mesma tela | Lista completa | Select profissional → um nome; select status → Cancelado; limpar; buscar nome fictício | Listagem reagindo a cada recorte | Idem | Busca por serviço/período inexistente não pode aparecer | Filtros/busca conferidos (A4–A6); nomes fictícios neutros |
| 5 | Modal de detalhes | Agendamento Confirmado fictício | Abrir modal; percorrer campos | Horário, cliente, profissional, serviço, preço plausível, status (+pagamento) | Close no modal | Campos de edição/remarcação inexistentes não podem surgir; preço R$ 12.000,00 proibido | Campos = matriz A7; preço plausível; sem dados reais |
| 6 | Cartão Pendente | 1 agendamento Pendente | Clicar Confirmar; recarregar página | Badge Pendente → Confirmado; persistência | Close no cartão/badge | Insinuar mensagem/automação | Apenas transição manual A8; nenhuma notificação exercitada |

Capturas estáticas de apoio (mesma sessão): repetir os 12 enquadramentos de 05/11 sobre a fixture editorial, em 450×800@2,4x, para referência de edição — classificadas como evidência técnica da nova sessão, nunca como frames finais sem revisão quadro a quadro.

## 4. Ausências registradas

- Gravação de tela das cenas 3–6: **inexistente** (bloqueada por aprovação).
- Ilustração da cena 2 e artes das cenas 1/7: **inexistentes** (produção após aprovação de identidade).
- Fixture editorial: **inexistente** (pré-requisito acima).
- SRT/narração NS-001 em `04-legendas/`: criados como **preliminares** nesta rodada (`ns001_roteiro_001.srt`, `ns001_roteiro_001_narracao.txt`), vinculados ao timing proposto do storyboard.

Nenhuma imagem simulada será apresentada como prova de funcionalidade: fixtures seguem rotuladas como fixture em todos os registros.