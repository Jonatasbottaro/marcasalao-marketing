# Plano de execução — HF-001

Fases da operação com estado real e evidência. Nada é marcado concluído sem evidência
executável registrada em [EVIDENCIAS.md](EVIDENCIAS.md).

| Fase | Escopo | Estado | Evidência |
| --- | --- | --- | --- |
| F0 | Auditoria Git: branches, commits não enviados, PRs, worktrees | ✅ Concluída | EVIDENCIAS F0; base escolhida `codex/operacao-resultado-26` (main+6, fast-forward) |
| F1 | Auditoria documental + inventários | ✅ Concluída | INVENTARIO-DOCUMENTAL, INVENTARIO-FUNCIONAL |
| F2 | Matriz de migração + decisão MKT-VIDEO-003 | ✅ Concluída | MATRIZ-DE-MIGRACAO; MKT-VIDEO-003; notas datadas em MKT-VIDEO-001/MKT-PIPELINE-001 |
| F3 | Instalação do runtime HyperFrames | ✅ Concluída | commit `89ef85f`; smoke verde (h264 1080×1920, 10.0 s, **0 streams de áudio**) |
| F4 | Skills HyperFrames | ✅ Concluída | commit `5d4465c`; 25 skills, lock v2 upstream `cfaefdc` |
| F5 | `frame.md` consumido por máquina | ✅ Concluída (via F6) | `adapter/tenant.mjs` parseia o frontmatter normativo (cores/tipografia/headerOverlay/áudio) |
| F6 | Adaptador contratos → composição → render | ✅ Concluída | `renderers/hyperframes/adapter/` + `tools/render_hyperframes.py`; smoke verde (render + guardrails); decisão CLI registrada |
| F7 | Integração Video Studio | ⬜ Pendente | Rotas aditivas em `video_studio.py`; pacote de entrega reutilizado |
| F8 | Fila: concorrência, progresso, recuperação | ⬜ Pendente | Item `hyperframes` na fila SQLite existente; estados/recovery preservados |
| F9 | Templates nativos (reel produto/funcionalidade/institucional, motion, horizontal) | ⬜ Pendente | `kind` de cena → template; geometrias dos perfis |
| F10 | Formatos de post/carrossel no motor de vídeo | ⬜ Pendente | 1080×1350, 1080×1080, 1080×1920, 1920×1080 (arte estática de feed segue ComfyUI08) |
| F11 | Preservação de geração de imagens IA | ✅ Sem ação | ComfyUI08 + guard de proveniência intocados (matriz #13) |
| F12 | Campanha piloto HF-PILOTO-001-MARCA-SALAO | ⬜ Pendente | Tema organização da agenda; post 4:5 + carrossel 4 cards + reel 20–25 s; capturas Meu Salão autorizadas com dados fictícios; VIDEO CLEAN |
| F13 | Avaliação visual + comparação Op24 v2 × HyperFrames | ⬜ Pendente | Pacote de revisão portável; sem aprovação estética sem ver |
| F14 | Testes (contratos, adaptador, operação, ffprobe, CI) | ⬜ Pendente | Gates legados preservados; novo gate HyperFrames aditivo |
| F15 | Política de atualização/manutenção | ✅ Concluída (doc) | ATUALIZACOES-E-ROLLBACK |
| F16 | Rollback | ✅ Concluída (doc) | ATUALIZACOES-E-ROLLBACK |
| F17 | Segurança e governança | 🔶 Em execução | Confinamento de caminhos no adaptador (F6); revisão de segredos na entrega |
| F18 | Commits e PRs (rascunho, sem merge) | 🔶 Em execução | Commits `89ef85f`, `5d4465c` enviados; PR A (governança/docs) em preparação |

## Ordem de execução a partir daqui

1. **PR A — governança e documentação** (F1/F2/F15/F16): docs da migração + MKT-VIDEO-003
   + notas datadas + atualização dos índices oficiais (`docs/README.md`,
   `docs/governanca/MAPA-DOCUMENTAL.md`, `docs/contexto/*`, `WORKFLOW.md`). ✅ commit `3fca35a`.
2. **PR B — fundação** (já na branch): runtime + skills (commits `89ef85f`, `5d4465c`). ✅
3. **F6 — adaptador** (`renderers/hyperframes/`): parser de `frame.md`, validação de
   guardrails, materialização de composição, ponte JSON, verificação `ffprobe`.
   Avaliar API `@hyperframes/producer` vs CLI. ✅ smoke verde.
4. **F7+F8 — Studio e fila**: rotas e tipo de item aditivos; testes de recovery.
5. **F9+F10 — templates nativos** por perfil de saída, sem claims proibidas.
6. **F12 — piloto** HF-PILOTO-001-MARCA-SALAO (produção nova completa, VIDEO CLEAN).
7. **F13 — avaliação visual** humana + comparação v2/v3 × HyperFrames.
8. **F14 — testes e CI** aditivos.
9. **F18 — PRs C (integração) e D (produção)**, relatório master A–AD, handoff.

## Regras de execução permanentes

- Cada fase deixa o estado recuperável: commit por bloco coeso, branch técnica
  enviada ao remoto, nada de rebase destrutivo, nada de merge para `main`.
- Suítes de teste longas rodam separadas (limite de 10 min por comando).
- Render sempre via wrappers (`hf.sh`/`hf-project.sh`) — nunca `npx` cru, nunca
  `source config/env.sh` em shell interativo (quebra identidade Git da sessão).
- Qualquer bloqueio é registrado como bloqueio, nunca contornado.
