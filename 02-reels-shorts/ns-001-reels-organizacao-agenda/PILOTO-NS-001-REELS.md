# Piloto de produção — NS-001 Reels "Organização e visibilidade da agenda"

## 1. Identificação da peça

| Campo | Valor |
| --- | --- |
| Campanha | ns-001 |
| Identificador da peça | NS-001-P001 |
| Nome da peça | Organização e visibilidade da agenda — Reels |
| Canal | instagram |
| Formato | reels |
| Variante | v1 |
| Posicionamento do CTA | legenda + bio (pendente de confirmação do link externo do perfil) |
| Destino candidato | https://marcasalao.com.br (pendente de confirmação do titular) |
| Formato de vídeo | vertical 9:16, 1080 × 1920, 30 fps, sem áudio |
| Duração alvo | 30 s (proposta; pendente de leitura cronometrada e confirmação editorial) |
| Hook | NS-001-H15 revisado: "Você consegue visualizar os agendamentos do seu salão com clareza?" |
| CTA | "Conheça a agenda do Marca Salão." |
| Status do roteiro | rascunho (aprovação editorial pendente) |
| Autorizado para gravação | não |
| Autorizado para publicação | não |

Este piloto é uma **entrega de preparação**. Outro operador deve conseguir abrir este diretório e continuar a produção: sequência por cena, inventário de mídias, rascunho de legenda/CTA e registro de publicação iniciado. Nenhuma gravação, render final ou publicação está autorizada nesta etapa.

## 2. Fonte editorial

- Briefing: `00-briefings/campanhas/NS-001/briefing.md` (v0.3, em validação)
- Roteiro: `03-roteiros/campanhas/NS-001/roteiro-001.md` (v0.3, rascunho)
- Hooks: `02-hooks/campanhas/NS-001/hooks.md` (NS-001-H15 selecionado para o roteiro 001)
- Validação funcional: `00-briefings/campanhas/NS-001/VALIDACAO-FUNCIONAL-AGENDA.md`
- Execução autenticada: `00-briefings/campanhas/NS-001/VALIDACAO-EXECUCAO-2026-11-05.md` (concluída 2026-11-05, emuladores + Chromium, dados fictícios)
- Capturas de evidência: `00-briefings/campanhas/NS-001/capturas/2026-11-05/` (12 arquivos, evidência técnica, não frames aprovados)

## 3. Sequência da peça por cena

A sequência segue a estrutura narrativa do roteiro 001 (seção 5):

```
Hook → Situação → Visões da agenda → Filtros e busca → Detalhes → Ação de status → CTA
```

| # | Cena | Duração alvo | Texto de tela | Ação | Mídia necessária | Referência ao roteiro |
|---|------|-------------|---------------|------|------------------|----------------------|
| 1 | Pergunta de clareza (hook) | 4 s | "Você consegue visualizar os agendamentos do seu salão com clareza?" | Texto em destaque sobre fundo da marca | Fundo identidade da marca (verde-petróleo, menta, branco); sem tela de produto | Roteiro Cena 1 |
| 2 | Situação de informação espalhada | 6 s | "Quando as informações ficam espalhadas, cada lugar mostra um pedaço do dia." | Exibir anotações, conversa e planilha em telas separadas | Imagens sem marca de produto (caderno, conversa, planilha) — fictícias | Roteiro Cena 2 |
| 3 | Visões dia, semana e mês | 6 s | "O mesmo registro, visto por dia, semana ou mês." | Acionar seletor "Dia"/"Semana"/"Mês" na agenda | Captura da agenda do gestor (visões dia/semana/mês) — nova captura com fixture editorial | Roteiro Cena 3 |
| 4 | Filtros e busca | 6 s | "Filtrar por profissional, por status, ou buscar pelo nome." | Alterar seletores e digitar nome no campo de busca | Captura da agenda com filtros por profissional/status e busca — nova captura com fixture editorial | Roteiro Cena 4 |
| 5 | Detalhes de agendamento fictício | 4 s | "Abrir um atendimento e ver os dados dele." | Abrir modal de detalhes de um agendamento fictício | Captura do modal de detalhes (horário, cliente, profissional, serviço, preço, status) — nova captura com fixture editorial | Roteiro Cena 5 |
| 6 | Ação de status comprovada | 2 s | "Atualizar o status do atendimento." | Executar ação manual "Confirmar" em agendamento fictício | Captura da ação Confirmar (Pendente → Confirmado) — nova captura com fixture editorial | Roteiro Cena 6 |
| 7 | Chamada para ação | 2 s | "Conheça a agenda do Marca Salão." | Arte final de marca com CTA; sem simular botão clicável | Arte final com identidade da marca — a ser criada | Roteiro Cena 7 |

**Total aproximado: 30 s** (duração alvo, pendente de leitura cronometrada e confirmação editorial).

### Regras aplicadas a todas as cenas
- Vídeo sem áudio; narração entregue como texto separado em `04-legendas/` (etapa própria).
- Legendas visíveis sincronizadas e `.srt` correspondente (etapa própria).
- Somente dados fictícios; nenhum dado real de cliente, telefone, e-mail, credencial.
- Sem exibir horários disponíveis, slots livres, criação, edição, remarcação, exclusão, duração como campo próprio, preenchimento automático.
- Sem mensagens, lembretes ou confirmações automáticas como promessa.
- Sem simular botão clicável em imagem estática (Cena 7).
- A interface capturada exibe "Meu Salão"; a campanha usa "Marca Salão" — decisão de nome oficial pendente do titular.

## 4. Inventário de mídias por cena

| Cena | Mídia | Pode ser reutilizado? | Precisa de nova captura? | Substituído por fictício no teste? | Detalhes para a captura que falta |
|------|-------|----------------------|--------------------------|-----------------------------------|-----------------------------------|
| 1 | Fundo identidade da marca | Parcial — artes aprovadas em `marcas/marcasalao/posts/` | Sim (adaptação vertical 1080×1920) | Sim, no teste de pré-voo | Fundo verde-petróleo/menta/branco com texto da pergunta em destaque; sem tela de produto |
| 2 | Anotações, conversa, planilha | Não | Sim | Sim, no teste de pré-voo | Imagens sem marca de produto; situação condicional ("quando"); sem classificar salão como desorganizado |
| 3 | Visões dia/semana/mês da agenda | Parcial — capturas `capturas/2026-11-05/` (evidência técnica) | Sim | Sim, no teste de pré-voo | Captura nova com fixture editorial; adaptação vertical; revisão de marca; revisão quadro a quadro; sem dados pessoais |
| 4 | Filtros por profissional/status + busca | Parcial — capturas `capturas/2026-11-05/` | Sim | Sim, no teste de pré-voo | Captura nova com fixture editorial; valores de status: Pendente, Confirmado, Concluído, Cancelado, No-show |
| 5 | Modal de detalhes (horário, cliente, profissional, serviço, preço, status) | Parcial — capturas `capturas/2026-11-05/` | Sim | Sim, no teste de pré-voo | Captura nova com dados fictícios completos e plausíveis; sem nome/telefone/e-mail reais |
| 6 | Ação Confirmar (Pendente → Confirmado) | Parcial — capturas `capturas/2026-11-05/` | Sim | Sim, no teste de pré-voo | Captura nova com persistência após recarga; nenhuma mensagem/notificação |
| 7 | Arte final com CTA | Não | Sim | Sim, no teste de pré-voo | Arte com identidade da marca; texto "Conheça a agenda do Marca Salão."; sem botão clicável desenhado |

### Critério de substituição por mídia fictícia
No teste de pré-voo (seção 5), todas as capturas da agenda são substituídas por imagens fictícias geradas por `tools/make_proof_assets.py` (stdout apenas), marcadas como `origin: synthetic-proof`. Isso permite executar o pipeline sem depender de capturas reais. Para a peça final, todas as mídias fictícias devem ser substituídas por capturas reais com fixture editorial, revisão de marca e aprovação do titular.

### Capturas que ainda faltam (para a peça final)
Todas as cenas 3 a 7 dependem de capturas novas com fixture editorial. As capturas de `capturas/2026-11-05/` são evidência técnica e **não** estão aprovadas como frames de publicação: trazem identificação técnica E2E ("Meu Salão E2E"), preço fictício de R$ 12.000,00 e enquadramento de validação.

## 5. Rascunho da legenda e do posicionamento do CTA

### Legenda (rascunho, pronta para receber o valor aprovado)

**Texto principal (tela e narração, Cena 7):**
> Conheça a agenda do Marca Salão.

**Destino:**
- `https://marcasalao.com.br` — endereço oficial documentado no repositório (AGENTS.md, "Chamadas para o site Marca Salão").
- O painel de demonstração (`https://marcasalao.com.br/gestor`) exige credenciais: **não** usar como destino público da campanha.

### Posicionamento do CTA por canal (condicional)

| Canal | Posicionamento | Texto do CTA | Link na bio / sticker | Status |
|-------|---------------|--------------|----------------------|--------|
| Instagram Reels | legenda | "Conheça a agenda do Marca Salão." | "link na bio" somente se o link externo do perfil estiver confirmado | pendente de confirmação |
| Instagram Stories | bio / sticker | "Conheça a agenda do Marca Salão." | sticker de link somente com autorização de publicação | pendente de confirmação + autorização |
| YouTube Shorts | descrição | "Conheça a agenda do Marca Salão." | URL completa na descrição | pendente de confirmação |
| TikTok | legenda/descrição | "Conheça a agenda do Marca Salão." | conforme política do canal | pendente de confirmação |

### Regras do CTA
- URL em legenda do Instagram **não é clicável**; botão desenhado em imagem **não gera** adesivo de link.
- Não prometer acesso direto ao painel `/gestor` (exige credenciais não armazenadas no repositório).
- Rastreamento: pendente — não há mecanismo de rastreamento definido. Registrar como "não rastreado", não como "sem resultado".

## 6. Registro de publicação iniciado

Preenchido com os campos já conhecidos do modelo de mensuração (`05-mensuracao/modelo-registro-publicacoes.csv`). Horário real, link público e métricas deixados vazios (ainda não coletados).

| Campo | Valor |
|---|---|
| id_peca | NS-001-P001 |
| campanha | ns-001 |
| canal | instagram |
| formato | reels |
| variante | v1 |
| posicao_cta | legenda + bio |
| data_hora_publicacao | (vazio — ainda não publicada) |
| link_publico | (vazio — ainda não publicada) |
| status_destino | pendente_de_decisao |
| url_destino | (vazio — depende de decisão do titular) |
| url_parametrizada | (vazio — depende de url_destino) |
| utm_source | (vazio — depende de decisão do titular) |
| utm_medium | (vazio — depende de decisão do titular) |
| utm_campaign | (vazio — depende de decisão do titular) |
| utm_content | (vazio — depende de decisão do titular) |

O registro completo segue o cabeçalho do modelo `05-mensuracao/modelo-registro-publicacoes.csv`:
`id_peca,campanha,canal,formato,variante,posicao_cta,data_hora_publicacao,link_publico,status_destino,url_destino,url_parametrizada,utm_source,utm_medium,utm_campaign,utm_content`

## 7. Prova local (seção seguinte)

O resultado do pré-voo e a causa do bloqueio do render real estão em `prova-local/`.

## 8. Limites e pendências

- Briefing, hook e roteiro **não aprovados** pelo titular.
- Gravação e publicação **não autorizadas**.
- Nenhuma métrica real coletada; linha de base não disponível.
- Destino clicável e link externo do perfil pendentes de confirmação do titular.
- Nome oficial da marca para uso público pendente ("Meu Salão" na interface vs. "Marca Salão" na campanha).
- CTA por canal pendente de validação.
- As capturas de `capturas/2026-11-05/` são evidência técnica, não frames aprovados.
