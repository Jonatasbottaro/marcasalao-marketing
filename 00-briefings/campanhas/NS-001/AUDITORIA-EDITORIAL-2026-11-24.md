# Auditoria editorial — NS-001 (24/11/2026)

- Campanha: NS-001 — Organização e visibilidade da agenda · Tenant: `marca-salao`
- Base auditada: briefing v0.3 (`briefing.md`, status **em validação**), hooks v0.3 (`../../../02-hooks/campanhas/NS-001/hooks.md`), roteiro-001 v0.3 (`../../../03-roteiros/campanhas/NS-001/roteiro-001.md`, rascunho).
- Evidências: [`VALIDACAO-FUNCIONAL-AGENDA.md`](VALIDACAO-FUNCIONAL-AGENDA.md) (leitura de código + testes selecionados, commit Salao02 `6342a33a36b0a4eadd0f5a62770f1eee485156ee`, 02/11/2026) e [`VALIDACAO-EXECUCAO-2026-11-05.md`](VALIDACAO-EXECUCAO-2026-11-05.md) (E2E local com emuladores + verificação manual autenticada em Chromium, 05/11/2026).
- Natureza: **proposta para aprovação do titular**. Nada neste documento aprova briefing, hook, roteiro, gravação ou publicação.
- Classificações usadas: confirmado por evidência · proposta editorial · hipótese · pendente de validação · não suportado · rejeitado anteriormente.

## 1. Os doze pontos da auditoria

| # | Ponto | Classificação | Achado |
| --- | --- | --- | --- |
| 1 | Clareza da dor | Confirmado por evidência (formulação) + pendente de validação (pesquisa) | A dor "dificuldade de visualizar e acompanhar os agendamentos com clareza" está bem formulada como pergunta de reconhecimento (briefing §4). Não existe pesquisa quantitativa com o público; frequência e impacto seguem hipótese. A campanha não afirma universalidade. |
| 2 | Identificação do público | Confirmado por evidência (definição qualitativa) | Gestores de pequenos salões com controle manual/fragmentado (briefing §3). Nível de conhecimento sobre o Marca Salão: hipótese. Sem dado demográfico — correto não usar nenhum. |
| 3 | Coerência da proposta de valor | Confirmado por evidência | Mensagem "Tenha mais clareza sobre os agendamentos do seu salão" e promessa permitida "Acompanhe os agendamentos do dia, da semana ou do mês em uma agenda organizada" correspondem exatamente às capacidades confirmadas (validação §4 e §9, execução 05/11). A formulação anterior com "horários disponíveis" foi rejeitada por evidência e permanece apenas como histórico. |
| 4 | Precisão técnica das afirmações | Confirmado por evidência | Todas as capacidades demonstradas nas cenas 3–6 constam da tabela da validação §4 e foram observadas em navegador autenticado (execução §2). As ausências (slots, criação, edição, remarcação, exclusão, duração própria, preenchimento automático) estão verificadas e respeitadas pelo roteiro. Matriz completa em [`MATRIZ-VERACIDADE-COMERCIAL.md`](MATRIZ-VERACIDADE-COMERCIAL.md). |
| 5 | Força da abertura | Proposta editorial | H15 revisado ("Você consegue visualizar os agendamentos do seu salão com clareza?") é claro, curto e seguro, mas abstrato: não nomeia uma cena concreta da rotina. Alternativas mais concretas existem na biblioteca (H03, H10) e são propostas como opções em [`RECOMENDACAO-HOOK-2026-11-24.md`](../../../02-hooks/campanhas/NS-001/RECOMENDACAO-HOOK-2026-11-24.md). Nenhum desempenho foi medido; não há vencedor de teste. |
| 6 | Continuidade narrativa | Confirmado por evidência (estrutura) | Hook → Situação → Visões → Filtros/busca → Detalhes → Confirmação manual → CTA: cada cena prepara a seguinte e todas as demonstrações são capacidades confirmadas. A cena 2 é condicional ("Quando…"), sem estatística invented. |
| 7 | Simplicidade da linguagem | Confirmado por evidência (texto) | PT-BR natural, frases curtas, sem jargão técnico, sem sensacionalismo. Vocabulário alinhado ao briefing (visualizar, acompanhar, clareza, rotina). |
| 8 | Legibilidade do texto em vídeo | Pendente de validação | Textos de tela cabem em 1080×1920 com quebra em 2–3 linhas; a cena 2 tem o texto mais longo (74 caracteres) e exige 3 linhas ou encurtamento proposto no storyboard. Tempos de leitura cronometrados por estimativa de locução natural estão no storyboard; a conferência final depende da gravação real. |
| 9 | Coerência do CTA | Confirmado por evidência (texto) + pendente de validação (canal) | "Conheça a agenda do Marca Salão." corresponde ao destino oficial `https://marcasalao.com.br` (briefing §12). Adaptação por canal (bio Instagram, URL completa Facebook, mecanismo YouTube) pendente de confirmação do titular; matriz em [`ADAPTACAO-CANAIS-E-UTM.md`](ADAPTACAO-CANAIS-E-UTM.md). |
| 10 | Diferenciação sem exageros | Confirmado por evidência | Nenhum superlativo, número sem fonte ou garantia de resultado. O diferencial é a leitura reunida do que já está registrado — não automação, não prevenção de faltas. Risco residual: "clareza" lida como resultado garantido; mitigado pela forma de pergunta e pela ausência de promessa de resultado. |
| 11 | Riscos de interpretação | Pendente de validação (decisões) | (a) Confusão agenda-do-gestor × fluxo público: mitigada por texto e por cena, manter vigilância na edição. (b) Nome "Meu Salão" na interface × "Marca Salão" na campanha: decisão do titular pendente (briefing §14; execução §6). (c) Capturas com identificação E2E e preço fictício de R$ 12.000,00: impróprias como frames finais — fixture editorial dedicada pendente. (d) Divergência de identidade visual brand-kit × artes publicadas: registrada em [`AUDITORIA-IDENTIDADE-VISUAL.md`](AUDITORIA-IDENTIDADE-VISUAL.md). |
| 12 | Dependências de aprovação | Pendente de validação | Briefing, hook, roteiro, textos de tela/narração, CTA por canal, identidade pública, responsável e autorização de gravação: todos pendentes do titular. Publicação é decisão separada e posterior. Checklist do roteiro §13 e do briefing §15 refletem isso corretamente. |

## 2. Pontos fortes

1. Cadeia de evidência exemplar: código → testes isolados → execução autenticada → capturas, cada nível com limites explícitos.
2. Separação correta entre superfície do gestor e fluxo público do cliente; a campanha não empresta capacidades de uma tela para outra.
3. Proibições comerciais (lembretes, automação, resultados garantidos) mantidas mesmo depois de a auditoria localizar implementação técnica de reminder — a precisão técnica mudou, a autorização não.
4. Histórico preservado sem contaminação: formulações rejeitadas (H01, mensagem com "disponíveis") marcadas como histórico, nunca como texto atual.
5. Proteção de dados: capturas inspecionadas uma a uma, sem telefone/e-mail/credencial; dados integralmente fictícios.

## 3. Problemas encontrados e correções propostas (priorizadas)

| Prioridade | Achado | Severidade | Correção proposta |
| --- | --- | --- | --- |
| P1 | Nenhuma aprovação editorial existe (briefing/hook/roteiro) | Bloqueante para produção | Pacote de aprovação com decisões objetivas (§K do pacote). Nada produzir antes. |
| P1 | Nome público e identidade visual sem decisão oficial ("Meu Salão" × "Marca Salão"; brand-kit × artes) | Bloqueante para frames finais | Recomendação fundamentada em [`AUDITORIA-IDENTIDADE-VISUAL.md`](AUDITORIA-IDENTIDADE-VISUAL.md); decisão do titular. Não alterar brand-kit nem produto. |
| P1 | CTA/destino/UTM por canal sem confirmação; link da bio não conferido | Bloqueante para publicação | Matriz com status `pendente_de_decisao`; candidatos preparados sem registro como ativos. |
| P2 | Capturas de 05/11 são evidência técnica, não frames (E2E visível, preço R$ 12.000,00, enquadramento desktop) | Necessita ajuste antes da gravação | Fixture editorial dedicada + plano de gravação em [`INVENTARIO-CAPTURAS-E-PLANO-GRAVACAO.md`](INVENTARIO-CAPTURAS-E-PLANO-GRAVACAO.md). |
| P2 | Produto sem revalidação desde 05/11; checkout local sem Git | Necessita ajuste antes da gravação | Nova execução autenticada local como pré-requisito do plano de gravação (runbook existente no Salao02). |
| P3 | Texto de tela da cena 2 longo para leitura móvel rápida | Recomendação | Versão curta proposta no storyboard, marcada como proposta de revisão (texto original preservado). |
| P3 | Narração da cena 5 enumera seis campos em uma frase | Recomendação | Mantida como referência; alternativa com pausa proposta no storyboard, cronometrada. |
| P4 | READMEs de 00-briefings/02-hooks/03-roteiros ainda usam a formulação absoluta "o sistema não envia lembretes" | Informação (pendência já registrada no briefing §14) | Fora do escopo desta rodada; manter registro para revisão documental futura. Não alterar nesta tarefa. |

## 4. Veracidade do produto hoje (FASE 2 — resumo)

- O checkout `D:/MEGA/Antigravity/Salao02` existe nesta estação, **sem metadados Git**; não é possível diffar contra `6342a33` nem confirmar identidade de commit. Repositório remoto privado (API pública 404). Nenhum arquivo do produto foi alterado.
- Consequência: a evidência de 02/11 + 05/11 permanece o registro válido; **a peça final exige nova verificação autenticada** antes da gravação, já incorporada ao plano de gravação como critério de aceite.
- Matriz linha a linha, com rastreabilidade de cada frase do roteiro: [`MATRIZ-VERACIDADE-COMERCIAL.md`](MATRIZ-VERACIDADE-COMERCIAL.md).

## 5. Parecer

**Pronto para revisão do titular.** O material editorial existente é coerente, rastreável e fiel à evidência; os bloqueios restantes são decisões do titular e preparação de material real (fixture + gravação), não defeitos de texto. Nenhuma aprovação foi criada ou alterada nesta auditoria.