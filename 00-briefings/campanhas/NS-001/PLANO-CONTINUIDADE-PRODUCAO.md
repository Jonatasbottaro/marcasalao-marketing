# Plano de continuidade — produção final da NS-001 (condicionado às aprovações)

Preparado em 24/11/2026. **Não executar automaticamente.** Cada passo só avança com a aprovação correspondente registrada pelo titular (portal/CLI de aprovações). Publicação é decisão separada, sempre manual.

1. **Aprovação formal do briefing e roteiro** — decisões 1–3 e 8 do pacote; registrar aprovador e data; hook aprovado (decisão 2) antes de qualquer gravação.
2. **Preparação de dados fictícios editoriais** — fixture dedicada conforme inventário (namespace próprio, nomes neutros, campos completos, preços plausíveis, estados Pendente/Confirmado/Concluído/Cancelado); somente Firestore Emulator; script descartável; produto intacto.
3. **Gravação atualizada da agenda** — nova execução autenticada de conferência (runbook local do Salao02) + gravação das cenas 3–6 em emulação 450×800@2,4x (1080×1920); decisões 4, 5 e 9 do pacote antes de gravar.
4. **Revisão quadro a quadro** — dados pessoais, identificadores E2E, preços, nome público, enquadramento e áreas seguras; capturas estáticas de apoio da mesma sessão.
5. **Montagem do VideoRequest** — `marca-salao-ns-001-p001-editorial-v1` com os tempos do storyboard aprovado (47 s propostos), 7 cenas, 3 perfis existentes; `--plan-only` antes do render.
6. **Criação do vídeo legendado sem áudio** — legendas queimadas do SRT recalculado; `-an`; zero faixas; narração permanece texto separado.
7. **Exportação para formatos aprovados** — perfis `instagram-reels-video`, `facebook-reels-video`, `youtube-shorts` (+ derivados 1:1/16:9 se aprovados); entregas em `.workspace/` com manifestos e hashes.
8. **Validação com FFprobe** — 0 faixas de áudio, geometria/fps/duração por perfil; `delivery_verify`; SRT válido e sincronizado.
9. **Revisão humana** — titular confere peça, legendas, narração externa e textos por canal; estado editorial registrado como aprovado somente com decisão real.
10. **Geração do pacote final** — ZIP + manifestos + evidências; handoff fail-closed (`factory_cli.py handoff --all-approved`) empacota apenas aprovados.
11. **Aprovação específica para publicação manual** — destino/CTA/bio/UTM confirmados (decisão 7); teste de aceite de destino completo; publicação/agendamento pelo titular, `autoPublish:false` preservado.

Bloqueios atuais que impedem o passo 1: nenhuma aprovação editorial existe. Passos 2–10 permanecem bloqueados em cascata até as decisões do pacote.