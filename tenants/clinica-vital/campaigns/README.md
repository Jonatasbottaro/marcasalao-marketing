# Campanhas do tenant `clinica-vital`

- `camp-saas-demo-clinica-vital-001.json`: jornada de marcação de avaliação em `/avaliacao/clinica-vital-centro` e acompanhamento na recepção em `/gestor/consultas` (`saas-demo`, 6 cenas, `30.0s`, sem áudio `-an`).
  - Superfície pública: `/avaliacao/[clinicId]` (`/avaliacao/clinica-vital-centro`)
  - Superfície da recepção: `/gestor/consultas`
  - Paciente fictícia em destaque: Patricia Monteiro
- `camp-saas-demo-clinica-vital-002.json`: rotina exclusiva da recepção em `/gestor/consultas` — filtro por especialista, atualização manual de status e busca por paciente, sem cenas de `/avaliacao` (`saas-demo`, 6 cenas, `30.0s`, sem áudio `-an`).

Notas de conformidade (saúde/clínicas):

- Sem promessa de cura, resultado estético garantido ou tratamento sem dor garantido.
- Sem diagnóstico médico/odontológico online, receita digital, prontuário sensível ou fotos de antes e depois.
- Sem mensagens automáticas, lembretes de 24h, WhatsApp/SMS/e-mail, redução de faltas ou aumento de faturamento.
- Sem checkout, pagamento ou cobrança simulada.
