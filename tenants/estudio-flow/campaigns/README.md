# Campanhas do tenant `estudio-flow`

- `camp-saas-demo-estudio-flow-001.json`: fluxo SaaS de reserva de aula experimental em Pilates & Bem-Estar (`saas-demo`, 6 cenas, `30.0s`, sem áudio `-an`).
  - Superfície pública: `/aulas/[studioId]` (`/aulas/estudio-flow-jardins`)
  - Superfície do gestor: `/gestor/turmas`
- `camp-saas-demo-estudio-flow-002.json`: rotina exclusiva da gestão interna em `/gestor/turmas` — filtro por instrutora da fixture, atualização manual de presença/status e busca por aluna, sem nenhuma cena de `/aulas` (`saas-demo`, 6 cenas, `30.0s`, sem áudio `-an`).
  - Superfície da gestão: `/gestor/turmas` (`manager-agenda`)
  - Sem superfície pública: nenhuma cena em `/aulas/[studioId]` (`public-booking`)
  - Instrutora em destaque: Clara Nogueira (`inst-ef-003`); aluna localizada na busca: Andréia Silveira (`turma-ef-004`)
  - Legendas: todas as linhas do `.srt` com no máximo 48 caracteres
