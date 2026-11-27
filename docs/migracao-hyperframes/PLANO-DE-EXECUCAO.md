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
| F7 | Integração Video Studio | ✅ Concluída | Rotas aditivas (`renderer/save`, `readiness`, `preview`); entrega reutilizada — commit `8ceb8d5`, prova `ci_hyperframes_queue_proof.py` verde (EVIDENCIAS F7/F8) |
| F8 | Fila: concorrência, progresso, recuperação | ✅ Concluída | Modalidade `hyperframes` na fila SQLite existente; estados/recovery preservados — commit `8ceb8d5`, prova HTTP verde (positivo/guardrails/recuperação) |
| F9 | Templates nativos (reel produto/funcionalidade/institucional, motion, horizontal) | ✅ Concluída | `narrativeFunction` → template no compositor (hook/demonstration/cta); geometrias genéricas — EVIDENCIAS F9/F10 |
| F10 | Formatos de post/carrossel no motor de vídeo | ✅ Concluída | Stills PNG via `snapshot` oficial: 1080×1350 e 1080×1080 verificados; 9:16/16:9 como vídeo; arte estática de feed segue ComfyUI08 — EVIDENCIAS F9/F10 |
| F11 | Preservação de geração de imagens IA | ✅ Sem ação | ComfyUI08 + guard de proveniência intocados (matriz #13) |
| F12 | Campanha piloto HF-PILOTO-001-MARCA-SALAO | ✅ Concluída | Post 4:5 + carrossel 4 cards + reel 24 s renderizados e verificados; capturas Studio Bella versionadas; VIDEO CLEAN; nada publicado (ver EVIDENCIAS) |
| F13 | Avaliação visual + comparação NS-001 v2 × HyperFrames | 🔶 Pacote pronto; revisão humana pendente | `review.html` + 3 relatórios + frames/storyboard + players v2 × HF; re-render byte-idêntico (40,7 s); **sem aprovação estética declarada** (ver EVIDENCIAS; corrigido em HF-002: 47 s é NS-001 v2/Resultado 08, não Op24) |
| F14 | Testes (contratos, adaptador, operação, ffprobe, CI) | ✅ Concluída (ressalvas registradas) | Smokes HF + determinismo dedicado verdes; 415/416 smoke Python e 1009/1017 platform com **falhas herdadas da base** (prova: arquivos idênticos a `3cf2fdc`); workflow rascunho `hyperframes-validation.yml` (dispatch-only) — ver EVIDENCIAS |
| F15 | Política de atualização/manutenção | ✅ Concluída (doc) | ATUALIZACOES-E-ROLLBACK |
| F16 | Rollback | ✅ Concluída (doc) | ATUALIZACOES-E-ROLLBACK |
| F17 | Segurança e governança | ✅ Concluída | Confinamento de caminhos (F6) + varreduras de segredos/nuvem com saída real (EVIDENCIAS F17) |
| F18 | Commits e PRs (rascunho, sem merge) | ✅ Concluída (bloqueio gh registrado) | Branch enviada (9 commits de fase + fechamento); PRs mapeados por faixa de commits + link manual (gh ausente); RELATORIO-MASTER A–AD versionado; **sem merge** |

## Ordem de execução a partir daqui

1. **PR A — governança e documentação** (F1/F2/F15/F16): docs da migração + MKT-VIDEO-003
   + notas datadas + atualização dos índices oficiais (`docs/README.md`,
   `docs/governanca/MAPA-DOCUMENTAL.md`, `docs/contexto/*`, `WORKFLOW.md`). ✅ commit `3fca35a`.
2. **PR B — fundação** (já na branch): runtime + skills (commits `89ef85f`, `5d4465c`). ✅
3. **F6 — adaptador** (`renderers/hyperframes/`): parser de `frame.md`, validação de
   guardrails, materialização de composição, ponte JSON, verificação `ffprobe`.
   Avaliar API `@hyperframes/producer` vs CLI. ✅ smoke verde.
4. **F7+F8 — Studio e fila**: rotas e tipo de item aditivos; testes de recovery. ✅ commit `8ceb8d5`.
5. **F9+F10 — templates nativos** por perfil de saída, sem claims proibidas. ✅ templates por `narrativeFunction` no compositor + stills PNG via `snapshot`; geometrias 1:1/4:5/9:16/16:9 verificadas.
6. **F12 — piloto** HF-PILOTO-001-MARCA-SALAO (produção nova completa, VIDEO CLEAN). ✅
   post/carrossel/reel reais verificados; refinamentos de contraste e convenção
   de stills registrados em EVIDENCIAS.
7. **F13 — avaliação visual** humana + comparação v2/v3 × HyperFrames. 🔶 pacote
   de revisão montado (`review.html`, relatórios, frames, players); decisão de
   aceite/ajuste pendente do titular — sem aprovação estética sem ver.
8. **F14 — testes e CI** aditivos. ✅ smokes + determinismo verdes; workflow
   rascunho criado; duas falhas herdadas da base registradas (fumo Python
   415/416 ambiental de worktree; platform 1 falha introduzida pelo Op 24
   `f01ed60`) — correção fora do escopo HF-001, dependência anotada para os PRs.
9. **F18 — PRs C (integração) e D (produção)**, relatório master A–AD, handoff. ✅
   concluída: branch completa enviada; PRs A/B/C/D mapeados por faixa de commits
   com link manual (bloqueio `gh` registrado); [RELATORIO-MASTER.md](RELATORIO-MASTER.md)
   versionado; handoff AGENTS.md no retorno final. **Operação encerrada nesta
   branch** — decisões restantes (revisão F13, PRs formais, gate, merge) são do
   titular (seção AC do relatório).

## Regras de execução permanentes

- Cada fase deixa o estado recuperável: commit por bloco coeso, branch técnica
  enviada ao remoto, nada de rebase destrutivo, nada de merge para `main`.
- Suítes de teste longas rodam separadas (limite de 10 min por comando).
- Render sempre via wrappers (`hf.sh`/`hf-project.sh`) — nunca `npx` cru, nunca
  `source config/env.sh` em shell interativo (quebra identidade Git da sessão).
- Qualquer bloqueio é registrado como bloqueio, nunca contornado.
