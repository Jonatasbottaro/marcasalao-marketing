# Adaptação por canal e matriz CTA/destino/UTM — NS-001 (24/11/2026)

Natureza: propostas. Nenhum link registrado como ativo; nenhum campo de destino confirmado preenchido; nenhuma publicação/agendamento. Convenções: `05-mensuracao/GUIA-MENSURACAO-NS001-NS002.md`, `06-validacao-destinos/GUIA-VALIDACAO-DESTINOS-NS001-NS002.md`, AGENTS.md (CTA por rede), `04-legendas/matriz-utm-consolidada.csv` (fonte canônica de URLs — **não alterada nesta rodada**).

Canais priorizados: **Instagram Reels, Facebook Reels, YouTube Shorts**. Stories/TikTok/WhatsApp Status: hipóteses do briefing, **não incluídos** sem aprovação explícita no briefing final.

## 1. Adaptação editorial por canal

### Instagram Reels
- Título: "A agenda do salão, vista com clareza"
- Hook: H15 revisado (pergunta de clareza) nos primeiros 5 s
- Mensagem principal: "Acompanhe os agendamentos do dia, da semana ou do mês em uma agenda organizada."
- CTA na peça: "Conheça a agenda do Marca Salão." (neutra na imagem)
- Legenda proposta: "Você consegue visualizar os agendamentos do seu salão com clareza? Na agenda do Marca Salão, o registro do dia, da semana e do mês fica reunido: filtros por profissional e status, busca por cliente e os dados de cada atendimento. Conheça o sistema — link na bio. #MarcaSalão #AgendaDoSalão #GestãoDeSalão"
- Hashtags: #MarcaSalão #AgendaDoSalão #GestãoDeSalão (3, pertinentes)
- Descrição: mesma da legenda (Reels não tem campo separado)
- URL candidata: `https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-reels-v1` — **status pendente_de_decisao**; "link na bio" somente se o link externo do perfil estiver conferido na data da publicação; URL em legenda não é clicável
- Orientação visual: master 9:16; legendas na faixa segura; sem botão desenhado
- Restrições técnicas: 1080×1920, 30 fps, H.264, 0 áudio (`-an`), SRT + narração externa; perfil `instagram-reels-video`
- Critérios de aprovação: briefing/hook/roteiro aprovados + bio conferida + destino aprovado pelo titular

### Facebook Reels
- Título: "Visualize os agendamentos do seu salão com clareza"
- Hook: idem
- Mensagem principal: idem
- CTA na peça: idem neutra
- Legenda proposta: "Você consegue visualizar os agendamentos do seu salão com clareza? Acompanhe os agendamentos do dia, da semana ou do mês em uma agenda organizada: filtros por profissional e status, busca por cliente e os dados de cada atendimento. Acesse pelo link da descrição: https://marcasalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=ns-001&utm_content=ns-001-p001-fbreels-v1"
- Hashtags: opcionais no Facebook; mesmas 3 se usadas
- Descrição: URL completa na legenda conforme política do projeto
- URL candidata: a acima — **pendente_de_decisao**
- Orientação visual: idem master
- Restrições técnicas: perfil `facebook-reels-video`, 1080×1920, 30 fps, 0 áudio
- Critérios de aprovação: destino aprovado + testes de aceite do guia de destinos

### YouTube Shorts
- Título: "A agenda do seu salão, organizada | Marca Salão"
- Hook: idem
- Mensagem principal: idem
- CTA na peça: idem neutra
- Legenda/descrição proposta: "Veja como a agenda do Marca Salão reúne os agendamentos do dia, da semana e do mês, com filtros por profissional e status, busca por cliente e detalhes de cada atendimento. Conheça o sistema: https://marcasalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=ns-001&utm_content=ns-001-p001-shorts-v1"
- Hashtags: #Shorts #MarcaSalão #AgendaDoSalão
- URL candidata: a acima — **pendente_de_decisao**; conferir o mecanismo de link vigente para Shorts na data da publicação (descrição/painel); não presumir clicabilidade em todo contexto
- Orientação visual: idem master
- Restrições técnicas: perfil `youtube-shorts`, 1080×1920, 30 fps, 0 áudio; duração proposta 47 s dentro do limite do formato
- Critérios de aprovação: destino aprovado + mecanismo de link conferido

## 2. Matriz CTA / destino / UTM

| Canal | Formato | CTA proposto | Destino | UTM | Status |
| --- | --- | --- | --- | --- | --- |
| Instagram | Reels | "Conheça a agenda do Marca Salão." + "link na bio" (somente confirmado) | https://marcasalao.com.br (candidato) | source=instagram, medium=reels, campaign=ns-001, content=ns-001-p001-reels-v1 | pendente_de_decisao |
| Facebook | Reels | idem + URL completa na legenda | idem | source=facebook, medium=reels, campaign=ns-001, content=ns-001-p001-fbreels-v1 | pendente_de_decisao |
| YouTube | Shorts | idem + link na descrição conforme mecanismo vigente | idem | source=youtube, medium=shorts, campaign=ns-001, content=ns-001-p001-shorts-v1 | pendente_de_decisao |

- Identificador estável da peça: **NS-001-P001** (variante `v1`), conforme guia de mensuração.
- `utm_campaign=ns-001` em minúsculo, conforme guia. As linhas existentes da `matriz-utm-consolidada.csv` para o pacote técnico `camp-saas-demo-ns001-agenda-001` permanecem intactas (`aguardando_aprovacao_titular`); esta campanha editorial usa a convenção do guia e só entra na matriz consolidada por decisão/fluxo oficial do titular.
- Painel autenticado (`/gestor`) **não** é destino de campanha.

## 3. Verificação de destino somente-leitura (observação, não aprovação)

Executada em 24/11/2026 por GET público com `-L` (sem sessão, sem credenciais):

| URL candidata | HTTP | Redirects | UTMs preservados na URL final |
| --- | --- | --- | --- |
| …utm_source=instagram…reels-v1 | 200 | 0 | sim |
| …utm_source=facebook…fbreels-v1 | 200 | 0 | sim |
| …utm_source=youtube…shorts-v1 | 200 | 0 | sim |

Passos 1–3 do teste de aceite do guia observados (carrega sem erro; URL final esperada; UTMs preservados). Passo 4 (ação da página corresponde ao CTA) **não avaliado por renderização** — permanece pendente. Aprovação exige teste `aprovado` + confirmação escrita do titular, conforme guia.

## 4. Bloqueios

- Link externo do perfil Instagram não conferido nesta estação (sem acesso autorizado) — "link na bio" não pode ser prometido ainda.
- Mecanismo de link do YouTube Shorts a conferir na data da publicação.
- Nenhuma UTM/destino entra como confirmado sem decisão do titular; nenhum evento de conversão configurado; nenhuma métrica inventada.