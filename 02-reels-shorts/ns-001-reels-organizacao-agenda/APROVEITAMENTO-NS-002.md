# Reaproveitamento do piloto NS-001 para a NS-002

## 1. O que pode ser reaproveitado do piloto NS-001

| Item | Pode ser reaproveitado? | Como aplicar na NS-002 |
|------|------------------------|------------------------|
| Formato de vídeo | Sim | Vertical 9:16, 1080 × 1920, 30 fps, sem áudio (mesma especificação do roteiro NS-002) |
| Modelo de mídia (vídeo-request + assets fictícios) | Sim | Mesmo esquema `VideoRequest v1` com `media[]` e `scenes[]`; assets fictícios gerados por `make_proof_assets.py` |
| Teste de destino (redirecionamento localhost) | Sim | Mesmo roteiro de redirecionamento: rota que repassa UTMs vs. rota que descarta query string; checagem de preservação de parâmetros |
| Kit de mensuração (CSV de publicações e métricas) | Sim | Mesmas colunas e convenção UTM (`utm_content = id_peca + variante`); `utm_content` vazio para bio compartilhada se o perfil não usar |
| Estrutura de cenas (hook → situação → demonstração → CTA) | Sim | Mesma sequência narrativa adaptada aos 3 momentos da NS-002 |
| Regra de vídeo sem áudio | Sim | Nenhum áudio; narração como texto separado; `.srt` sincronizado |
| Pipeline de render local (`produce_video.py` + `render_pipeline.py`) | Sim | Mesma CLI, mesmo fluxo de pré-voo e render; diferenças apenas no pedido e nos assets |

## 2. Telas e dados fictícios necessários para a NS-002

A NS-002 mostra a sequência de agendamento prevista no briefing (fluxo público do cliente → agenda do gestor). São necessárias as seguintes capturas com fixture editorial:

| Tela | Momento do roteiro NS-002 | Dados fictícios necessários |
|------|--------------------------|----------------------------|
| `/booking/[salonId]` — "Primeiro, seus dados" | Momento 1 (a cliente escolhe) | Nome, sobrenome, telefone fictícios plausíveis |
| `/booking/[salonId]` — "Escolha um Serviço" | Momento 1 | Serviço fictício com nome, preço e duração plausíveis |
| `/booking/[salonId]` — seleção de profissional | Momento 1 | Profissional fictício aprovado e vinculado ao serviço |
| `/booking/[salonId]` — calendário e horário | Momento 2 (a cliente confirma) | Dia e horário `HH:MM` selecionados; sem exibir regras internas |
| `/booking/[salonId]` — confirmação | Momento 2 | Mensagem de sucesso da interface; sem cobrança como promessa |
| `/gestor/agenda` — mesmo atendimento | Momento 3 (o salão vê) | Mesmo serviço, cliente e profissional fictícios; enquadramento vertical |
| (opcional) `/cliente/bookings` — Meus Agendamentos | Evidência de apoio | Não é cena obrigatória; inserto de até 1 s |

Todas as capturas devem usar dados fictícios, sem telefone/e-mail/credenciais reais, sem namespace `e2e-...`, sem ambiente de produção.

## 3. Cenas, decisões editoriais e provas que ainda bloqueiam a primeira peça da NS-002

| Bloqueio | Tipo | Detalhe |
|----------|------|---------|
| Aprovação do briefing NS-002 | Editorial | Briefing em validação; aprovação parcial (2026-11-16) só para hooks e roteiro; produção bloqueada |
| Aprovação do roteiro NS-002 | Editorial | Roteiro 001 em rascunho; não autorizado para gravação nem publicação |
| Capturas com fixture editorial | Produção | Nenhuma captura das 7 telas acima foi feita; capturas de 2026-11-05 são evidência técnica da ponta do gestor, não frames aprovados |
| Link externo do perfil (bio) | Decisão do titular | Pendente: confirmar link cadastrado no Instagram antes de usar "link na bio" |
| Autorização de sticker de link | Decisão do titular | Pendente: sticker somente com autorização separada de publicação |
| Destino clicável confirmado | Decisão do titular | `https://marcaselao.com.br` como destino; confirmação por canal |
| Mecanismo de rastreamento | Decisão do titular | Pendente: não há utm/pixel definido; registrar como "não rastreado" |
| Nome da marca na interface | Decisão do titular | Interface exibe "Meu Salão"; campanha usa "Marca Salão"; decisão pendente antes das capturas finais |
| Render local (ffmpeg/ffprobe) | Técnico | ffmpeg/ffprobe não disponíveis nesta estação; necessário para produzir MP4 final |

## 4. Próximo passo imediato para a NS-002

Após o Jonatas aprovar o briefing e o roteiro, o próximo passo é:
1. Criar worktree `docs/piloto-producao-ns002` a partir de `origin/main`.
2. Montar o `VideoRequest v1` da NS-002 com as 6 cenas (30s) e assets fictícios.
3. Executar pré-voo e render local (quando ffmpeg estiver disponível).
4. Preencher registro de publicação e métricas usando o kit de mensuração.
