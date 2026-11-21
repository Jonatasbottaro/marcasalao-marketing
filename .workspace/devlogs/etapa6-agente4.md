# Devlog — Etapa 6 / Agente 4 (fechamento do ciclo de growth com importador UTM)

> **Data:** 2026-11-20  
> **Branch/worktree:** `codex/etapa6-agente4` em `.workspace/worktrees/etapa6-agente4`  
> **Base:** `main` @ `8a1b361` (Etapa 5B consolidada, 5 tenants, 10 campanhas, 40 slots)  
> **Escopo:** importador/analisador de performance UTM, playbook, CI e testes

## 1. Objetivo

Fechar o elo que faltava no ciclo de growth: transformar os CSVs exportados do GA4,
Plausible ou Umami (mais o log manual de hook A/B) em um relatório executivo cruzado
com o calendário editorial — por tenant, canal, onda e variante de hook — sem simular
receita e sem alterar posts.

## 2. Entregas

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `tools/utm_report_importer.py` | novo | API `analyze_performance`/`generate_template` + CLI, 100% stdlib |
| `tools/tests/test_utm_report_importer.py` | novo | 16 testes cobrindo os 3 provedores, auto, rankings, hooks, não atribuído, template, contenção e CLI |
| `docs/analytics-utm-playbook.md` | atualizado | seção 8 com o fluxo semanal fechado, formato do hook log e tabela de colunas por provedor; referências renumeradas |
| `.github/workflows/local-render-validation.yml` | atualizado | `test_srt_formatter.py`, `test_approval_cli.py`, `test_utm_report_importer.py` e `test_workspace_doctor.py` na suíte do CI |
| `.workspace/devlogs/etapa6-agente4.md` | novo | este relatório |

## 3. Desenho do importador

### 3.1 Normalização multi-provedor

- `auto` pontua cabeçalhos por marcadores distintos (GA4 usa `Session *`;
  Plausible usa `utm_*` + `visitors`; Umami usa `source/medium/campaign/content` +
  `views/events`). Empate ou zero marcadores vira erro explícito pedindo `--provider`.
- Aliases canônicos aceitam variações reais de exportação: GA4
  `Session manual ad content`/`Session manual content`; Plausible
  `visitors`/`visits`; Umami `views`, `events`; conversões GA4 também aceitam
  `Key events`.
- Números toleram vírgula de milhar e vírgula decimal; linhas inválidas são
  registradas em `dataQuality.invalidRows` em vez de derrubar a execução.

### 3.2 Cruzamento e atribuição

- Chave de junção: `(utm_source, utm_medium, utm_campaign, utm_content)`.
- Fonte primária `04-legendas/calendario-editorial.json`; fallback automático para
  `04-legendas/matriz-utm-consolidada.csv` quando o JSON não existe.
- Linhas sem par vão para `unmatchedRows` com motivo `UTM_NOT_IN_CALENDAR`; a execução
  continua com `ok: true`.
- Chaves duplicadas no calendário são expostas em `dataQuality.duplicateCalendarKeys`.

### 3.3 Hook A/B

- Variante pode vir da coluna `hook_variant_used` do CSV ou de `--hook-log`.
- O log aceita três formatos: lista em `hooks` com `slot_id`, lista com
  `utm_campaign`+`utm_content`, ou mapa direto `{"slot-001": "A"}`.
- Precedência: log manual sobre a coluna do CSV.
- Comparativo `rankings.byHook` só aparece quando há variante informada.

### 3.4 Rankings e relatório

- `rankings.byTenant`, `byChannel`, `byWave` (rótulos fixos
  `Onda 1 9:16` e `Onda 2 1:1/16:9`) e `byHook`, ordenados por conversões e sessões.
- Dimensões são semeadas com todos os valores do calendário (inclusive zero) para
  evidenciar cobertura.
- Saídas em `--out-dir`: `utm-performance-report.json` e `utm-performance-report.md`.
- `financialSimulation: false`; nenhum campo monetário é calculado ou inferido.

### 3.5 Template e contenção

- `--generate-template <csv>` exporta as 40 linhas da matriz com as colunas
  `sessions`, `engaged_sessions`, `conversions` e `hook_variant_used` vazias.
- CSV de entrada, hook log, calendário e `--out-dir` precisam ficar dentro da raiz;
  caminho externo retorna `PATH_OUTSIDE_ROOT` (exit 2).

## 4. Evidências

```
$ python -m unittest tools/tests/test_utm_report_importer.py tools/tests/test_utm_simulator.py -v
Ran 28 tests — OK
# 16 do importador + 12 do simulador

$ smoke end-to-end com o calendário real (CSV GA4 de 7 linhas, 6 casadas)
provider=ga4 ok=True
totals: 7 linhas, 6 casadas, 1 não atribuída, 2490 sessões, 139 conversões (5.58%)
byChannel: youtube 1510/82 (5.43%) · instagram 680/47 (6.91%) · facebook 300/10 (3.33%)
byWave: Onda 1 9:16 2090/99 · Onda 2 1:1/16:9 400/40 (10.0%)
byHook: Hook A 1720/88 · Hook B 680/47
byTenant: marca-salao 2400, clinica-vital 90, demais 0 (semeados)
unmatched: tiktok/bio/camp-xyz/ghost (reportado, sem falhar)
```

O smoke também confirmou `utm-performance-report.md` com tabelas de totais, canal,
onda, tenant, hooks, não atribuídos e qualidade de dados.

## 5. Limitações

- Os aliases cobrem os formatos descritos na tarefa e variações comuns de exportação;
  exportações com cabeçalhos muito diferentes devem usar `--provider` explícito ou
  ganhar novo alias.
- O importador exige arquivos dentro da raiz do projeto (regra de portabilidade);
  exports baixados devem ser movidos para `.workspace/tmp/` antes de rodar.
- Nenhuma receita, ROAS ou cobrança é simulada; o relatório é descritivo.
- `test_srt_formatter.py`, `test_approval_cli.py` e `test_workspace_doctor.py` são de
  agentes paralelos e podem ainda não existir nesta branch; foram adicionados ao CI
  conforme o contrato de integração.

## 6. Handoff

- Branch `codex/etapa6-agente4` com commit limpo.
- Verificação rápida:
  `python tools/utm_report_importer.py --root . --metrics-csv <csv> --out-dir .workspace/tmp/utm-report/<semana> --json`
- `contexto_projeto.md` não foi editado; este devlog é a fonte para `devlog_sync.py`
  na consolidação.