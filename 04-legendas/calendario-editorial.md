# Calendário Editorial — Content Factory Multi-Tenant

> Gerado por `tools/campaign_calendar.py --start-date 2026-11-23`.
> Período sugerido: **2026-11-23** a **2026-11-26** — 8 campanhas de 4 tenants, 24 slots (8 campanhas × 3 canais), até 2 campanhas por dia.
> Publicação 100% manual: `autoPublish: false` em todos os slots.
> Status editorial: `aguardando_aprovacao_titular` — nenhuma publicação sem aprovação expressa do titular.

## 1. Cronograma editorial (ordem cronológica)

| Slot | Data sugerida | Janela | Tenant | Marca | Campanha | Canal | Formato | Áudio |
|---|---|---|---|---|---|---|---|---|
| slot-001 | 2026-11-23 | 12:00-13:00 | multitrack-hub | Multitrack Hub | `camp-shorts-completo-multitrack-001` | Instagram Reels | reels | com áudio |
| slot-002 | 2026-11-23 | 12:00-13:00 | marca-salao | Marca Salão | `camp-saas-demo-marca-salao-001` | Instagram Reels | reels | `-an` (sem áudio) |
| slot-003 | 2026-11-23 | 18:00-19:00 | multitrack-hub | Multitrack Hub | `camp-shorts-completo-multitrack-001` | YouTube Shorts | shorts | com áudio |
| slot-004 | 2026-11-23 | 18:00-19:00 | marca-salao | Marca Salão | `camp-saas-demo-marca-salao-001` | YouTube Shorts | shorts | `-an` (sem áudio) |
| slot-005 | 2026-11-23 | 19:00-20:00 | multitrack-hub | Multitrack Hub | `camp-shorts-completo-multitrack-001` | Facebook Reels | reels | com áudio |
| slot-006 | 2026-11-23 | 19:00-20:00 | marca-salao | Marca Salão | `camp-saas-demo-marca-salao-001` | Facebook Reels | reels | `-an` (sem áudio) |
| slot-007 | 2026-11-24 | 12:00-13:00 | meu-salao | Meu Salão | `camp-saas-demo-meu-salao-001` | Instagram Reels | reels | `-an` (sem áudio) |
| slot-008 | 2026-11-24 | 12:00-13:00 | multitrack-hub | Multitrack Hub | `camp-shorts-rateios-002` | Instagram Reels | reels | com áudio |
| slot-009 | 2026-11-24 | 18:00-19:00 | meu-salao | Meu Salão | `camp-saas-demo-meu-salao-001` | YouTube Shorts | shorts | `-an` (sem áudio) |
| slot-010 | 2026-11-24 | 18:00-19:00 | multitrack-hub | Multitrack Hub | `camp-shorts-rateios-002` | YouTube Shorts | shorts | com áudio |
| slot-011 | 2026-11-24 | 19:00-20:00 | meu-salao | Meu Salão | `camp-saas-demo-meu-salao-001` | Facebook Reels | reels | `-an` (sem áudio) |
| slot-012 | 2026-11-24 | 19:00-20:00 | multitrack-hub | Multitrack Hub | `camp-shorts-rateios-002` | Facebook Reels | reels | com áudio |
| slot-013 | 2026-11-25 | 12:00-13:00 | estudio-flow | Estúdio Flow | `camp-saas-demo-estudio-flow-001` | Instagram Reels | reels | `-an` (sem áudio) |
| slot-014 | 2026-11-25 | 12:00-13:00 | marca-salao | Marca Salão | `camp-saas-demo-ns001-agenda-001` | Instagram Reels | reels | `-an` (sem áudio) |
| slot-015 | 2026-11-25 | 18:00-19:00 | estudio-flow | Estúdio Flow | `camp-saas-demo-estudio-flow-001` | YouTube Shorts | shorts | `-an` (sem áudio) |
| slot-016 | 2026-11-25 | 18:00-19:00 | marca-salao | Marca Salão | `camp-saas-demo-ns001-agenda-001` | YouTube Shorts | shorts | `-an` (sem áudio) |
| slot-017 | 2026-11-25 | 19:00-20:00 | estudio-flow | Estúdio Flow | `camp-saas-demo-estudio-flow-001` | Facebook Reels | reels | `-an` (sem áudio) |
| slot-018 | 2026-11-25 | 19:00-20:00 | marca-salao | Marca Salão | `camp-saas-demo-ns001-agenda-001` | Facebook Reels | reels | `-an` (sem áudio) |
| slot-019 | 2026-11-26 | 12:00-13:00 | meu-salao | Meu Salão | `camp-saas-demo-meu-salao-002` | Instagram Reels | reels | `-an` (sem áudio) |
| slot-020 | 2026-11-26 | 12:00-13:00 | multitrack-hub | Multitrack Hub | `camp-shorts-stems-workflow-003` | Instagram Reels | reels | com áudio |
| slot-021 | 2026-11-26 | 18:00-19:00 | meu-salao | Meu Salão | `camp-saas-demo-meu-salao-002` | YouTube Shorts | shorts | `-an` (sem áudio) |
| slot-022 | 2026-11-26 | 18:00-19:00 | multitrack-hub | Multitrack Hub | `camp-shorts-stems-workflow-003` | YouTube Shorts | shorts | com áudio |
| slot-023 | 2026-11-26 | 19:00-20:00 | meu-salao | Meu Salão | `camp-saas-demo-meu-salao-002` | Facebook Reels | reels | `-an` (sem áudio) |
| slot-024 | 2026-11-26 | 19:00-20:00 | multitrack-hub | Multitrack Hub | `camp-shorts-stems-workflow-003` | Facebook Reels | reels | com áudio |

## 2. Checklist pré-publicação (por slot)

1. **Aprovação do titular:** o slot só entra em produção após aprovação expressa; o status editorial é `aguardando_aprovacao_titular`.
2. **Publicação manual:** nenhuma ferramenta publica ou agenda sozinha (`autoPublish: false`); publicar direto na rede ou via Postiz, conforme autorização do titular.
3. **Mídia e integridade:** conferir no pacote `04-legendas/pacotes-publicacao/<tenant>/<slug>/checklist-publicacao.json` os hashes SHA-256 (`sha256_disk_ok: true`) antes de anexar o vídeo.
4. **Legenda por canal:** usar o arquivo do canal no pacote (`instagram-reels.md`, `youtube-shorts.md`, `facebook-reels.md`), incluindo a URL UTM do slot exatamente como gerada.
5. **Instagram:** CTA "Conheça o sistema — link na bio"; conferir o link externo real cadastrado no perfil antes de prometer o acesso.
6. **Facebook e YouTube:** URL completa na descrição com "Acesse pelo link da descrição"; não simular botão clicável na imagem.
7. **Locução externa (tenants `-an`: `estudio-flow`, `marca-salao`, `meu-salao`):** o vídeo é entregue sem faixa de áudio; a narração de `<slug>_narracao.txt` é gravada fora do editor, pelo titular, quando desejado — não é requisito para publicar o vídeo legendado.
8. **Tenants com áudio próprio (`multitrack-hub`):** o vídeo já sai com a faixa de áudio permitida pelo guardrail do tenant.
9. **UTM:** não alterar os parâmetros UTM de posts já publicados; qualquer mudança invalida o histórico de dados.
10. **Analytics:** enquanto a ferramenta de analytics estiver PENDENTE (`docs/rastreio-utm.md`, seção 5), não declarar links UTM como ativos em registros de campanha.

## 3. Matriz UTM consolidada (8 campanhas × 3 canais = 24 URLs)

| Tenant | Campanha | Canal | URL rastreada |
|---|---|---|---|
| estudio-flow | `camp-saas-demo-estudio-flow-001` | Instagram Reels | https://estudioflow.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=estudio-flow |
| estudio-flow | `camp-saas-demo-estudio-flow-001` | YouTube Shorts | https://estudioflow.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=estudio-flow |
| estudio-flow | `camp-saas-demo-estudio-flow-001` | Facebook Reels | https://estudioflow.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=estudio-flow |
| marca-salao | `camp-saas-demo-marca-salao-001` | Instagram Reels | https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | `camp-saas-demo-marca-salao-001` | YouTube Shorts | https://marcasalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | `camp-saas-demo-marca-salao-001` | Facebook Reels | https://marcasalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | `camp-saas-demo-ns001-agenda-001` | Instagram Reels | https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-ns001-agenda-001&utm_content=marca-salao |
| marca-salao | `camp-saas-demo-ns001-agenda-001` | YouTube Shorts | https://marcasalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-ns001-agenda-001&utm_content=marca-salao |
| marca-salao | `camp-saas-demo-ns001-agenda-001` | Facebook Reels | https://marcasalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-ns001-agenda-001&utm_content=marca-salao |
| meu-salao | `camp-saas-demo-meu-salao-001` | Instagram Reels | https://meusalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | `camp-saas-demo-meu-salao-001` | YouTube Shorts | https://meusalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | `camp-saas-demo-meu-salao-001` | Facebook Reels | https://meusalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | `camp-saas-demo-meu-salao-002` | Instagram Reels | https://meusalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-002&utm_content=meu-salao |
| meu-salao | `camp-saas-demo-meu-salao-002` | YouTube Shorts | https://meusalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-meu-salao-002&utm_content=meu-salao |
| meu-salao | `camp-saas-demo-meu-salao-002` | Facebook Reels | https://meusalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-002&utm_content=meu-salao |
| multitrack-hub | `camp-shorts-completo-multitrack-001` | Instagram Reels | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-completo-multitrack-001` | YouTube Shorts | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-completo-multitrack-001` | Facebook Reels | https://multitrackhub.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-rateios-002` | Instagram Reels | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-shorts-rateios-002&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-rateios-002` | YouTube Shorts | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-shorts-rateios-002&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-rateios-002` | Facebook Reels | https://multitrackhub.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-shorts-rateios-002&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-stems-workflow-003` | Instagram Reels | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-shorts-stems-workflow-003&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-stems-workflow-003` | YouTube Shorts | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-shorts-stems-workflow-003&utm_content=multitrack-hub |
| multitrack-hub | `camp-shorts-stems-workflow-003` | Facebook Reels | https://multitrackhub.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-shorts-stems-workflow-003&utm_content=multitrack-hub |

> [!IMPORTANT]
> Enquanto a ferramenta de analytics (seção 5 de `docs/rastreio-utm.md`) estiver como PENDENTE,
> nenhum link UTM acima deve ser declarado como ativo em registros de campanha.
