# NS-001 — Pacote de aprovação editorial (24/11/2026)

**Estado: PRONTO PARA REVISÃO DO TITULAR.** Nada neste pacote está aprovado, gravado ou publicado. Aprovação de publicação é decisão separada e posterior.

Campanha NS-001 — Organização e visibilidade da agenda · Tenant `marca-salao` · Peça estável NS-001-P001 (v1 proposta).
Documentos de suporte (mesma pasta, salvo indicação): [auditoria editorial](AUDITORIA-EDITORIAL-2026-11-24.md) · [matriz de veracidade](MATRIZ-VERACIDADE-COMERCIAL.md) · [recomendação de hook](../../../02-hooks/campanhas/NS-001/RECOMENDACAO-HOOK-2026-11-24.md) · [storyboard](../../../03-roteiros/campanhas/NS-001/storyboard-001.md) · [identidade visual](AUDITORIA-IDENTIDADE-VISUAL.md) · [capturas e plano de gravação](INVENTARIO-CAPTURAS-E-PLANO-GRAVACAO.md) · [canais e UTMs](ADAPTACAO-CANAIS-E-UTM.md) · [plano de produção e qualidade](PLANO-PRODUCAO-VIDEO-STUDIO.md) · narração e SRT preliminares em `04-legendas/ns001_roteiro_001_*`.

## A. Resumo da campanha

- **Nome:** NS-001 — Organização e visibilidade da agenda.
- **Objetivo:** gerar interesse em conhecer a agenda do Marca Salão e solicitar uma demonstração.
- **Público:** gestores de pequenos salões que controlam horários de forma manual ou fragmentada (definição qualitativa; sem pesquisa demográfica).
- **Dor:** dificuldade de visualizar e acompanhar os agendamentos com clareza (pergunta de reconhecimento, sem universalidade).
- **Mensagem principal:** "Tenha mais clareza sobre os agendamentos do seu salão."
- **Benefício demonstrável:** leitura reunida do que já está registrado — visões dia/semana/mês, filtros por profissional e status, busca por cliente, detalhes e confirmação manual (todos confirmados por código + execução autenticada de 05/11/2026).
- **CTA proposto:** "Conheça a agenda do Marca Salão."

## B. Hook recomendado

**NS-001-H15 revisado:** "Você consegue visualizar os agendamentos do seu salão com clareza?" — pergunta curta (~4 s), fiel à evidência, sem disponibilidade/automação. Alternativas com justificativa e riscos: H03 (cena concreta da semana) e H10 (contraste de processos). Nenhum desempenho medido; seleção é editorial, não teste A/B.

## C. Roteiro final proposto (7 cenas, 47,0 s)

| Cena | Texto de tela | Narração (resumo) | Duração | Demonstração |
| --- | --- | --- | --- | --- |
| 1 | Pergunta de clareza | idem | 5,0 s | Arte de marca |
| 2 | Informação espalhada (condicional) | caderno/conversa/planilha | 11,0 s | Ilustração sem produto |
| 3 | O mesmo registro por dia/semana/mês | idem | 8,5 s | Gravação real das visões |
| 4 | Filtrar por profissional/status ou buscar nome | idem | 6,5 s | Gravação real dos filtros |
| 5 | Abrir um atendimento e ver os dados | campos do modal | 7,5 s | Gravação real do modal |
| 6 | Atualizar o status do atendimento | confirmação manual registrada | 5,5 s | Gravação real Pendente→Confirmado |
| 7 | Conheça a agenda do Marca Salão | idem | 3,0 s | Arte de CTA |

Textos integrais no storyboard e na narração separada. Duas propostas de ajuste rastreáveis (texto curto da cena 2; narração da cena 5 em duas frases) — originais preservados.

## D. Storyboard

Completo em [`storyboard-001.md`](../../../03-roteiros/campanhas/NS-001/storyboard-001.md): 15 campos por cena (objetivo, função narrativa, duração cronometrada, material visual, fonte de evidência, textos, enquadramento, transição, marca, legibilidade móvel, risco, dependência de captura, status). Áreas seguras e regras globais declaradas.

## E. Identidade visual

- **Divergência registrada:** artes públicas aprovadas (verde-petróleo/menta/branco, MS/tesoura — conferidas visualmente na arte PUBLICADA de 01/11/2026) × brand-kit técnico (amarelo/azul/verde/fundo escuro, Arial) × nome da interface "Meu Salão".
- **Recomendação (opção A):** identidade pública aprovada nas artes e fundos; brand-kit mantido como contrato de legendas/overlay da fábrica; recorte da gravação exclui a sidebar até decisão de nome. Opções B/C documentadas.
- **Pendência:** escolha do titular; nenhum arquivo de marca ou produto alterado.

## F. Textos comerciais

Legendas e adaptações por rede em [`ADAPTACAO-CANAIS-E-UTM.md`](ADAPTACAO-CANAIS-E-UTM.md): Instagram Reels (link na bio somente confirmado), Facebook Reels (URL completa na legenda), YouTube Shorts (mecanismo a conferir). Stories/TikTok/WhatsApp não incluídos sem aprovação.

## G. Narração e SRT

- `04-legendas/ns001_roteiro_001_narracao.txt` — PT-BR, por cenas e tempos, para uso externo; **nenhum áudio gerado**.
- `04-legendas/ns001_roteiro_001.srt` — **PRELIMINAR**, 9 cues, tempos do storyboard (47,0 s); recalcular contra a gravação real; sincronização definitiva não declarada.
- Checklist de legibilidade no arquivo de narração e no plano de qualidade.

## H. Capturas

- **Existentes:** 12 PNGs de 05/11/2026 (9 desktop 1440×900 + 3 mobile 390×844) — evidência técnica, inspecionadas sem dados sensíveis; **não** são frames finais (E2E visível, preço R$ 12.000,00, proporção inadequada).
- **Pendentes:** gravação real das cenas 3–6 com fixture editorial dedicada; ilustração da cena 2; artes 1/7.
- **Plano de gravação:** ambiente local com emuladores, emulação 450×800@2,4x = 1080×1920, sequência de interações e critérios de aceite por cena; nova conferência autenticada do produto como pré-requisito (checkout local sem Git impede diff desde 05/11).

## I. CTA e UTMs

Matriz com status `pendente_de_decisao` para os três canais; `utm_campaign=ns-001`, `utm_content=ns-001-p001-<variante>-v1`; destino candidato `https://marcasalao.com.br`. GET público somente-leitura: HTTP 200, 0 redirects, UTMs preservados (observação, não aprovação). Linhas da matriz UTM consolidada existentes intactas.

## J. Checklist de riscos

- [x] Nenhuma afirmação de slots/disponibilidade na agenda do gestor.
- [x] Nenhuma promessa de mensagens/lembretes/confirmação automática (implementação técnica existe; entrega não validada; proibição comercial mantida).
- [x] Nenhum resultado garantido (faltas, faturamento, ocupação).
- [x] Nenhum dado real/credencial nas capturas; dados fictícios.
- [x] Cena 2 condicional, sem estatística inventada.
- [ ] Nome público e identidade visual decididos — **pendente**.
- [ ] Fixture editorial e gravação nova — **pendentes**.
- [ ] CTA/destino/bio/UTM confirmados — **pendentes**.
- [ ] Aprovações editoriais registradas — **pendentes**.

## K. Decisões solicitadas ao titular

1. Aprovar ou solicitar ajustes no **briefing v0.3**.
2. Aprovar o **hook recomendado** (H15 revisado) ou escolher alternativa (H03/H10).
3. Aprovar o **roteiro de sete cenas** e as duas propostas de ajuste de texto.
4. Escolher a **identidade visual pública** (opção A recomendada) e o nome oficial ("Marca Salão" × "Meu Salão").
5. Autorizar a **preparação das capturas editoriais** (fixture + plano de gravação).
6. Confirmar os **canais** (IG Reels, FB Reels, YT Shorts).
7. Confirmar **CTA e destino por canal**, inclusive link da bio e UTMs.
8. Aprovar **textos de tela e narração**.
9. Autorizar **gravação e produção final** em etapa posterior.

**Publicação/agendamento: decisão separada e posterior, sempre manual.**

## L. Parecer editorial

**Pronto para revisão do titular.** Material coerente, rastreável e fiel à evidência; bloqueios restantes são decisões do titular e preparação de material real. QA editorial strict: 14 campanhas, 0 problemas. Nenhuma aprovação fictícia criada; estados editoriais reais preservados (briefing em validação; hook/roteiro rascunho; gravação/publicação: não).