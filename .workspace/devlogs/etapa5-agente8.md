# Etapa 5B — Agente 7 de 8: Growth & Analytics (auditoria e simulação UTM)

> O nome de arquivo `etapa5-agente8.md` é o definido no pedido; o executor é o
> **Agente 7** da rodada Etapa 5B (Engenheiro de Growth & Analytics).

- **Branch isolada:** `codex/etapa5b-agente7`
- **Worktree:** `<RAIZ>/.workspace/worktrees/etapa5b-agente7`
- **Base:** `main` @ `3f8cb1a92755b72a1283a4182acc93b4814df919` (worktree já existia;
  não foi recriada, conforme regra 1 do pedido).
- **Data:** 2026-11-20
- **Território exclusivo:** `tools/utm_simulator.py`,
  `tools/tests/test_utm_simulator.py`, `docs/analytics-utm-playbook.md` e
  `.workspace/devlogs/etapa5-agente8.md`. `contexto_projeto.md` não foi tocado.

## Contexto de partida

Já existia na main uma implementação anterior do Agente 4 (`e05c46e`) nos mesmos
três arquivos de território. Foi lida antes de qualquer escrita e seu comportamento
útil foi preservado (auditoria de domínio, parâmetros, colisões, URLs derivadas,
simulação determinística, contenção de path, CLI). A versão desta branch atende aos
requisitos específicos do pedido: eventos recomendados com os nomes exatos
`view_booking_page`, `select_service_or_class`, `request_evaluation` e
`inspect_multitrack_split`, e colisão definida sobre a **tupla completa**
`(utm_source, utm_medium, utm_campaign, utm_content)` entre tenants distintos.

## Arquivos alterados

| Arquivo | Conteúdo |
| --- | --- |
| `tools/utm_simulator.py` | API `audit_and_simulate_utm(root, calendar_path, simulate_traffic, out_dir, seed)` e CLI com `--calendar`, `--simulate-traffic`, `--out-dir`, `--json`, `--root`, `--seed`. 100% stdlib (sem dependência de módulo local). Descoberta de tenants em `tenants/*/brand-kit.json`, auditoria de 100% das URLs do calendário + URLs derivadas de campanhas de tenants ainda não agendados, verificação de HTTPS/domínio exato, quatro parâmetros obrigatórios com formato limpo, `utm_campaign == slug`, colisão da tupla de atribuição e contenção de caminhos. Simulação sintética determinística das duas ondas (Reels 9:16, Shorts 9:16, Feed 1:1, Vídeo 16:9) com eventos por nicho e `revenueBRL: null`. |
| `tools/tests/test_utm_simulator.py` | 12 testes `unittest`. |
| `docs/analytics-utm-playbook.md` | Guia de conversões por nicho em GA4, Plausible e Umami, códigos de auditoria, checklist pré-publicação e rotina semanal com `matriz-utm-consolidada.csv`. |
| `.workspace/devlogs/etapa5-agente8.md` | Este relatório. |

## Cobertura dos testes

1. auditoria real de todas as URLs do calendário (40 slots, 5 tenants);
2. detecção de domínio divergente;
3. detecção de colisão de atribuição entre tenants;
4. cobertura de tenant descoberto em `tenants/*` e ainda não agendado (URL derivada);
5. `--simulate-traffic`: arquivos gerados, duas ondas, três formatos, sem receita;
6. contenção de path (`out-dir` e `calendar` fora da raiz);
7. CLI `--json`;
8. parâmetro ausente e valor sujo;
9. HTTPS e campanha igual ao slug;
10. catálogo fechado dos quatro eventos recomendados;
11. determinismo da seed;
12. CLI retorna `1` quando a auditoria reprova.

## Evidências

```text
python -m unittest tools/tests/test_utm_simulator.py -v
Ran 12 tests in 0.342s — OK

python tools/utm_simulator.py --json
ok=True; urlsAudited=40; urlsOk=40; derivedUrls=0;
totalUrls=40; unscheduledTenants=[]; collisions=0

python tools/utm_simulator.py --simulate-traffic --out-dir .workspace/tmp/utm-sim --json
ok=True; sessoes=210; conversoes=17;
formatos=16:9, 1:1, 9:16; onda-1=170, onda-2=40
arquivos: utm_sessions_sample.json (145312 bytes), utm_attribution_summary.md (1763 bytes)
```

Todos os `revenueBRL` das sessões são nulos; nenhuma transação financeira é simulada.
Os arquivos de simulação ficaram em `.workspace/tmp/utm-sim/` (local, fora do Git).

## Limites e governança

- Não publica, agenda, edita posts publicados nem altera outras marcas.
- Não gera áudio, TTS, música nem faixa sonora (política de vídeo sem áudio).
- `contexto_projeto.md`, `rastreio-utm.md`, `matriz-utm-consolidada.csv` e
  `calendario-editorial.json` não foram alterados.
- A ferramenta de analytics segue como decisão pendente do titular; o playbook é
  operacional, mas não declara links UTM como ativos.

## Handoff

Commit realizado nesta branch, sem merge na main (consolidação a cargo do titular).
A worktree permanece registrada e não foi removida — remoção exige autorização.
Nenhum arquivo relacionado ao projeto foi criado fora de `<RAIZ>`.
