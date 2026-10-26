# Multitrack Hub — Controle total na mixagem

Data editorial: 25/10/2026. Fuso: America/Sao_Paulo.

## Estado: PARCIALMENTE AGENDADO / PUBLICADO PREMATURAMENTE

**Tentativa de agendamento para 25/10/2026 11:00 (America/Sao_Paulo) = 2026-10-25T14:00:00Z autorizada pelo titular.**

### Resultado real via CLI `posts:status --status schedule`:

- **Facebook** (`cmvna52ie0000msa3c12n995c`, canal `cmvbss5fn0005msbhhbdy6ing`): **PUBLISHED** imediatamente em 2026-10-25T03:39:57Z (estado original do rascunho). Não ficou agendado para 14:00:00Z. O CLI não permite definir nova data de agendamento; ao mudar de DRAFT para QUEUE, usou a data original do rascunho (passada) e publicou na hora.

- **Instagram** (`cmvna59910001msa3dtbvlanm`, canal `cmvbsudg50007msbh2j4734i4`): **QUEUE** (agendado) mas com `publishDate` 2026-10-25T03:39:57Z (data original do rascunho), não 14:00:00Z. Como essa data já passou, o comportamento real é incerto (pode publicar a qualquer momento ou ficar preso).

### Limitação técnica identificada
As ferramentas disponíveis (MCP `integrationSchedulePostTool` cria novo post; `postSettingsTool` não altera `publishDate`; CLI `posts:status` só altera DRAFT↔QUEUE sem parâmetro de data) **não permitem reagendar um rascunho existente para novo horário futuro**. A única via seria criar NOVOS posts com `type: schedule` e a data desejada, mas isso viola a instrução de não usar ferramenta de criação como substituta e geraria duplicatas.

### Arte e legendas
Preservadas inalteradas na pasta local. Hash da imagem conferido: `07d749bf39a3dd00571c3775d350642f432c99f936ed316791ea1b2b9ce27e93`.

### Próximos passos necessários (fora do escopo desta execução)
1. Avaliar se o post Facebook publicado prematuramente deve ser mantido ou removido manualmente no Postiz/Meta.
2. Corrigir o agendamento do Instagram (remover o QUEUE errado e criar novo agendado para 14:00:00Z, ou publicar manualmente no horário).
3. Registrar decisão do titular.

### Fontes e conformidade
- Site oficial: https://multitrackhub.com.br/como-funciona
- Identidade visual: repositório swnsolucoes/Multitrack
- Sem WhatsApp/telefone. Não misturar com Marca Salão.
