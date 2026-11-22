# Playbook de Analytics & Atribuição UTM — Fábrica Multi-Tenant

> **Versão:** 1.1 · **Data:** 2026-11-20 · **Autor:** Agente 7 da Etapa 5B (Growth & Analytics)
> **Escopo:** 5 tenants com brand-kit (`marca-salao`, `meu-salao`, `estudio-flow`,
> `multitrack-hub`, `clinica-vital`) · 10 campanhas · 40 slots em duas ondas.
> **Status:** guia operacional; a ferramenta de analytics ainda precisa ser escolhida
> pelo titular. Publicação continua manual e condicionada à aprovação expressa.

Este playbook complementa [rastreio-utm.md](rastreio-utm.md). A fonte canônica de
parâmetros e URLs continua sendo `04-legendas/matriz-utm-consolidada.csv`, gerada por
`tools/campaign_calendar.py` a partir de `04-legendas/calendario-editorial.json`.
Aqui ficam o catálogo de eventos por nicho, a configuração em GA4/Plausible/Umami,
a validação pré-publicação com `tools/utm_simulator.py` e a rotina semanal.

---

## 1. Convenções de rastreio

- URL padrão: `https://<domain-do-tenant>/?utm_source=...&utm_medium=...&utm_campaign=...&utm_content=...`
- O domínio é o campo `domain` de `tenants/<tenantId>/brand-kit.json` — auditoria exige
  HTTPS e host **exatamente igual**, sem `www` e sem redirecionamento que perca a query.
- `utm_campaign` é sempre o slug completo da campanha (`camp-...`), igual ao diretório
  da entrega em `02-reels-shorts/deliveries/<tenantId>/<slug>/`.
- **Onda 1 (lançamento 9:16):** `utm_content=<tenantId>`; formatos Reels (Instagram/Facebook)
  e Shorts (YouTube).
- **Onda 2 (reaproveitamento):** `utm_content=repurpose-1x1` (Instagram Feed, 1:1) ou
  `repurpose-16x9` (YouTube Vídeo, 16:9).
- Pares canal/mídia: `instagram/reels`, `instagram/feed`, `youtube/shorts`,
  `youtube/video`, `facebook/reels`.
- Valores em minúsculas, alfabeto `[a-z0-9._-]`, sem espaço nem acento.

| Tenant | Domínio oficial | Nicho |
| --- | --- | --- |
| `marca-salao` | `marcasalao.com.br` | SaaS de agenda para salões |
| `meu-salao` | `meusalao.com.br` | SaaS de agendamento/atendimentos |
| `estudio-flow` | `estudioflow.com.br` | Aulas e turmas (pilates/bem-estar) |
| `multitrack-hub` | `multitrackhub.com.br` | Multitracks, stems e rateios |
| `clinica-vital` | `clinicavital.com.br` | Saúde (consultas e avaliações) |

> Regra de atribuição: a tupla `(utm_source, utm_medium, utm_campaign, utm_content)`
> é única por tenant. O auditor rejeita qualquer colisão dessa tupla entre tenants distintos.

---

## 2. Eventos recomendados por nicho

O simulador usa um catálogo fechado de quatro eventos. Crie exatamente estes nomes
na ferramenta escolhida, **por tenant**, antes da primeira publicação com link rastreado:

| Tenant | Evento de conversão recomendado | Onde disparar |
| --- | --- | --- |
| `marca-salao` | `view_booking_page` | visualização da página de agendamento online |
| `meu-salao` | `view_booking_page` | visualização da página de agendamento |
| `estudio-flow` | `select_service_or_class` | seleção de serviço/aula na grade de turmas |
| `clinica-vital` | `request_evaluation` | solicitação de avaliação/consulta |
| `multitrack-hub` | `inspect_multitrack_split` | inspeção da separação de stems/rateio |

Regras comuns:

1. Nome em `snake_case`, sem prefixo de canal. A comparação entre canais é feita por
   `utm_source`/`utm_medium`, não pelo nome do evento.
2. Anexar ao evento as propriedades `tenant`, `utm_campaign` e `utm_content` (quando
   disponíveis). Nunca incluir dados pessoais (nome, e-mail, telefone).
3. Marcar o evento como conversão/objetivo **antes** da primeira coleta: métricas
   passadas não são recuperadas quando a meta é criada depois.
4. Reprodução social não é conversão. Contar apenas ações no site de destino.
5. Não simular receita, cobrança ou ROI. A simulação local mantém `revenueBRL` nulo.

### 2.1 Propriedades sugeridas por evento

| Evento | Propriedades obrigatórias | Propriedades opcionais |
| --- | --- | --- |
| `view_booking_page` | `tenant`, `utm_campaign`, `utm_content` | `wave` (`onda-1`/`onda-2`) |
| `select_service_or_class` | `tenant`, `utm_campaign`, `utm_content` | `service_id` (código interno, sem PII) |
| `request_evaluation` | `tenant`, `utm_campaign`, `utm_content` | `specialty` (código interno) |
| `inspect_multitrack_split` | `tenant`, `utm_campaign`, `utm_content` | `split_id` (código do pacote) |

---

## 3. Configuração no GA4

Pré-requisito: uma propriedade GA4 por domínio de tenant.

1. Admin → Data streams → Web: instalar a Google tag (`gtag.js`) no template base
   das cinco propriedades.
2. Confirmar que nenhum redirect descarta `utm_*` (testar com a URL exata de um slot).
3. Admin → Custom definitions → criar dimensões de evento `tenant` e `utm_content`,
   ambas com escopo *Event*.
4. Instrumentar os eventos do catálogo anexando os UTMs da URL:

```html
<script>
  function trackUtmEvent(name, tenant) {
    const q = new URLSearchParams(window.location.search);
    gtag('event', name, {
      tenant,
      utm_source: q.get('utm_source') || '',
      utm_medium: q.get('utm_medium') || '',
      utm_campaign: q.get('utm_campaign') || '',
      utm_content: q.get('utm_content') || ''
    });
  }
  // ex.: no clique do CTA da página de agendamento
  document.querySelector('#cta-agendamento')
    ?.addEventListener('click', () => trackUtmEvent('view_booking_page', 'marca-salao'));
</script>
```

5. Admin → Events: marcar `view_booking_page`, `select_service_or_class`,
   `request_evaluation` e `inspect_multitrack_split` como conversões na propriedade
   correspondente (um evento por tenant, conforme a tabela da seção 2).
6. Validar em Admin → DebugView com uma URL da matriz em janela anônima.
7. Leitura: Relatórios → Aquisição → Origem/mídia mostra `utm_source / utm_medium`;
   em Explorações usar *Session campaign* e a dimensão `utm_content` para comparar
   `repurpose-1x1` contra `repurpose-16x9`.

---

## 4. Configuração no Plausible

1. Criar um site por domínio (nuvem `plausible.io` ou self-hosted) e inserir o script
   com `data-domain="<domínio>"` no `<head>`.
2. O Plausible captura automaticamente `utm_source`, `utm_medium`, `utm_campaign` e
   `utm_content` como propriedades de sessão.
3. Site Settings → Goals: criar uma meta de evento por evento do catálogo da seção 2,
   com o nome exato (`view_booking_page`, etc.).
4. Instrumentar no site:

```html
<script>
  plausible('request_evaluation', {
    props: { tenant: 'clinica-vital', wave: 'onda-2' }
  });
</script>
```

5. Funnels: usar as metas criadas e filtrar por `utm_content=repurpose-1x1` ou
   `repurpose-16x9` para comparar a Onda 2 com a Onda 1.
6. Top Sources → aba UTM: isolar `utm_campaign` para comparar campanhas do mesmo tenant.
7. Validar em tempo real antes de publicar.

---

## 5. Configuração no Umami

1. Criar um website por domínio no painel Umami e inserir o script de rastreamento.
2. Website Settings → habilitar rastreamento UTM (`utm_source`, `utm_medium`,
   `utm_campaign`, `utm_content`).
3. Instrumentar eventos:

```html
<script>
  umami.track('inspect_multitrack_split', {
    tenant: 'multitrack-hub',
    utm_campaign: new URLSearchParams(location.search).get('utm_campaign') || ''
  });
</script>
```

4. Reports → Events: filtrar por propriedade `utm_campaign` para acompanhar uma
   campanha específica e por `tenant` para isolar o nicho.
5. Validar com uma URL real da matriz antes de publicar.

---

## 6. Validação pré-publicação com `utm_simulator.py`

A auditoria cobre 100% das URLs do calendário e de campanhas descobertas em `tenants/*`
ainda não agendadas:

```bash
python tools/utm_simulator.py --json
python tools/utm_simulator.py --calendar 04-legendas/calendario-editorial.json --json
```

Prova de fio das duas ondas (sem transação financeira):

```bash
python tools/utm_simulator.py --simulate-traffic \
  --out-dir .workspace/tmp/utm-sim --json
```

Saídas: `utm_sessions_sample.json` (sessões sintéticas, `revenueBRL: null`) e
`utm_attribution_summary.md` (resumo por nicho, onda e formato).

### 6.1 Códigos de auditoria

| Código | Severidade | Ação |
| --- | --- | --- |
| `DOMINIO_DIVERGENTE` | erro | host difere do `domain` exato do brand-kit |
| `ESQUEMA_NAO_HTTPS` | erro | URL sem HTTPS |
| `URL_SEM_HOST` / `UTM_URL_AUSENTE` | erro | slot sem URL utilizável |
| `UTM_PARAM_AUSENTE` | erro | falta um dos quatro parâmetros obrigatórios |
| `UTM_VALOR_NAO_PADRONIZADO` | erro | maiúscula, espaço, acento ou fora de `[a-z0-9._-]` |
| `UTM_PARAM_DUPLICADO` | erro | parâmetro repetido na mesma URL |
| `UTM_CAMPANHA_DIVERGENTE` | erro | `utm_campaign` difere do slug |
| `COLISAO_ATRIBUICAO` | erro | tupla de 4 UTMs repetida entre tenants |
| `TENANT_SEM_DOMINIO` / `TENANT_DESCONHECIDO` | erro | brand-kit ausente ou sem `domain` |
| `EVENTO_FORA_DO_CATALOGO` | erro | evento simulado fora do catálogo da seção 2 |

Exit codes: `0` aprovado · `1` auditoria reprovada · `2` erro de caminho/uso.

### 6.2 Checklist antes de liberar um slot

1. `ok: true` e `totalUrls == urlsAudited == urlsOk`.
2. `derivedUrls` conferido (campanhas novas ainda não agendadas).
3. `collisions: []` e `unscheduledTenants` revisado.
4. Evento do nicho criado e marcado como conversão na ferramenta escolhida.
5. Teste de ponta a ponta em janela anônima com a URL exata do slot.
6. `statusEditorial: aguardando_aprovacao_titular` e `autoPublish: false`.
7. Registrar data, slot, ferramenta e evidência no diário da campanha.

---

## 7. Rotina semanal com `matriz-utm-consolidada.csv`

Fonte: `04-legendas/matriz-utm-consolidada.csv` (UTF-8, LF, 20 colunas). Colunas
usadas na análise: `slot_id`, `onda`, `semana`, `data_sugerida`, `tenant_id`, `slug`,
`canal`, `formato_video`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`,
`utm_url`, `status_editorial`, `auto_publish`.

### 7.1 Segunda-feira (30 min)

1. Exportar da ferramenta escolhida as sessões e conversões agrupadas por
   `utm_source`, `utm_medium`, `utm_campaign` e `utm_content`.
2. Juntar com a matriz pela chave
   `(tenant_id, slug, utm_source, utm_medium, utm_content)`.
3. Calcular por linha:
   - `CVR = conversões / sessões`;
   - `share_conversoes = conversões da linha / conversões do tenant`;
   - `delta_onda2 = CVR(Onda 2) − CVR(Onda 1)` por tenant.
4. Comparar canais **dentro do mesmo tenant**; nunca comparar CVR entre nichos
   diferentes (funis e eventos são distintos).
5. Sinalizar anomalias: slot com 0 sessões após 72 h, CVR acima de 3× a mediana
   do tenant, `utm_content` inesperado no relatório (URL fora da matriz), colisão
   de atribuição.
6. Registrar decisões no diário. Ajuste de UTM vale apenas para slots futuros:
   **nunca editar post publicado para "corrigir" parâmetro**.

### 7.2 Saída da rotina

- Tabela curta por tenant: campanha, canal, formato, sessões, conversões, CVR.
- Top 3 e bottom 3 de `utm_content` por tenant (comparação das variantes A/B).
- Lista de anomalias com `slot_id` e ação recomendada para o próximo ciclo.

A execução prática desta rotina, a partir do CSV exportado do provedor, está na
seção 8 (`tools/utm_report_importer.py`).

---

## 8. Fechamento semanal com `utm_report_importer.py`

O importador fecha o ciclo: ingere o CSV exportado do provedor, normaliza os
cabeçalhos, cruza com o calendário/matriz e grava um relatório executivo por
tenant, canal, onda e variante de hook. É 100% stdlib e não simula receita.

### 8.1 Fluxo semanal (segunda-feira)

1. Exportar o CSV de sessões/conversões do provedor escolhido (GA4, Plausible ou
   Umami), agrupado por `utm_source`, `utm_medium`, `utm_campaign` e `utm_content`.
2. Se preferir preencher manualmente, gerar o template com as 40 linhas da matriz:

```bash
python tools/utm_report_importer.py \
  --generate-template .workspace/tmp/utm-report/metrics-semana-01.csv --json
```

3. Registrar qual hook foi publicado por slot (`A` ou `B`). O log é opcional quando
   o CSV já traz a coluna `hook_variant_used`:

```json
{"hooks": [{"slot_id": "slot-001", "variant": "A"}]}
{"hooks": [{"utm_campaign": "camp-x", "utm_content": "marca-salao", "hook_variant": "B"}]}
{"slot-001": "A", "slot-002": "B"}
```

4. Rodar o importador (o provedor é detectado automaticamente):

```bash
python tools/utm_report_importer.py \
  --metrics-csv .workspace/tmp/utm-report/metrics-semana-01.csv \
  --provider auto \
  --hook-log .workspace/tmp/utm-report/hooks-semana-01.json \
  --out-dir .workspace/tmp/utm-report/semana-01 --json
```

5. Ler `utm-performance-report.md` (executivo) e arquivar o JSON no diário da
   semana. Nenhum post é alterado e nenhum número de receita é inferido.

### 8.2 Colunas aceitas por provedor

| Campo canônico | GA4 | Plausible | Umami |
| --- | --- | --- | --- |
| source | `Session source` | `utm_source` / `source` | `source` / `utm_source` |
| medium | `Session medium` | `utm_medium` / `medium` | `medium` / `utm_medium` |
| campaign | `Session campaign` | `utm_campaign` / `campaign` | `campaign` / `utm_campaign` |
| content | `Session manual ad content` / `Session manual content` | `utm_content` / `content` | `content` / `utm_content` |
| sessions | `Sessions` | `visitors` / `visits` | `views` / `visits` |
| engaged | `Engaged sessions` | `engaged visitors` | `engaged views` |
| conversions | `Conversions` / `Key events` | `conversions` | `events` / `conversions` |

`--provider auto` usa marcadores distintos de cada exportação; se houver
ambiguidade, o erro pede `--provider ga4|plausible|umami`.

### 8.3 Saída e leitura

- `totals`: linhas, cobertura (`matchedRows`), tráfego não atribuído, sessões,
  conversões, CVR e engajamento.
- `rankings.byChannel`, `rankings.byWave` (`Onda 1 9:16` vs `Onda 2 1:1/16:9`),
  `rankings.byTenant` e `rankings.byHook` (`Hook A` vs `Hook B`).
- `unmatchedRows`: tráfego fora da matriz — sinalizado **sem reprovar** a execução;
  investigar `utm_content` inesperado ou campanha criada fora do calendário.
- `slots`: detalhe por `slotId`, incluindo CVR e variante de hook usada.

### 8.4 Regras de consistência

1. `--out-dir`, CSV, hook log e calendário precisam ficar dentro da raiz do projeto.
2. O log de hooks sobrescreve a coluna `hook_variant_used` quando os dois existem.
3. Linha sem `utm_content` válido cai em `unmatchedRows`; não editar post publicado
   para "corrigir" UTM — corrigir no próximo slot.
4. O relatório é insumo de leitura, não autorização de publicação.

### 8.5 Comparativo Hook A × Hook B (`rankings.hookComparison`)

- **Escopo:** por campanha (`byCampaign`) e agregado por tenant (`byTenant`), com sessões, conversões, CVR, engajamento, lift e classificação.
- **Critério estatístico:** teste z de duas proporções sobre `conversões/sessões`, implementado só com a biblioteca padrão (`math.erfc`) — determinístico e reproduzível em qualquer estação, sem scipy e sem rede.
- **Vencedor só com significância:** `|z| >= 1,96` **e** `p < 0,05` (95% de confiança). Diferença observada sem significância vira `empate_tecnico`, com recomendação de manter o teste A/B.
- **Amostra mínima por variante:** `--min-hook-sessions` (padrão 100 sessões) e `--min-hook-conversions` (padrão 5 conversões). Abaixo de qualquer um dos dois, `amostra_insuficiente` — nunca vencedor.
- **Campos por linha:** `classification`, `classificationLabel`, `classificationReason`, `zScore`, `pValue` e `significant`; os parâmetros do teste ficam em `statistics` (`method: two_proportion_z`, `alpha`, `zThreshold`, `minSessions`, `minConversions`).
- **Consumo no calendário:** `campaign_calendar.py --utm-report <relatorio.json>` traduz a classificação em `hookRecomendado` e `prioridadeHook` **apenas como recomendação**: datas, canais, UTMs e textos não mudam, e a decisão de trocar o hook continua sendo do titular.

### 8.6 Detecção de fadiga de hook e benchmarks por tenant (`rankings.tenantBenchmarks`)

A Etapa 9 acrescenta duas camadas ao relatório de performance UTM: detecção temporal de fadiga de hook e consolidação isolada por `tenant_id`.

#### 8.6.1 Detecção de fadiga de hook (`_detect_hook_fatigue`)

Compara a CVR (conversões/sessões) entre duas janelas temporais — janela inicial (Onda 1) e janela final (Onda 2) — para o mesmo hook/tenant/campanha:

- **Fadiga detectada (`fadiga_detectada`):** a CVR caiu estatisticamente da janela inicial para a final (`z >= 1,96` **e** `p < 0,05`, 95% de confiança). O hook está desgastando e deve ser revisado.
- **Estável (`estavel`):** houve diferença observada, mas sem significância estatística consistente. Manter o teste A/B em curso.
- **Amostra insuficiente (`amostra_insuficiente`):** qualquer das janelas tem menos de `--min-hook-conversions` (padrão 5) conversões ou menos de 1 sessão. Não há base para concluir.

**Campos expostos por linha:** `fatigueStatus`, `fatigueZScore`, `fatiguePValue`, `fatigueDetected` (bool) e `fatigueReason`. A amostra mínima respeita `--min-hook-conversions`.

#### 8.6.2 Benchmarks isolados por tenant (`rankings.tenantBenchmarks`)

Consolida métricas de forma **estritamente isolada por `tenant_id`** — nenhuma métrica de um tenant vaza para outro:

- Total de campanhas, sessões, sessões engajadas, conversões, CVR, taxa de engajamento e slots.
- **Taxa de vitória A/B (`abWinRatePct`):** proporção de campanhas classificadas como `vencedor_A` ou `vencedor_B` sobre o total de campanhas comparadas no tenant.
- **Hooks com fadiga (`hooksComFadiga`):** verdadeiro quando a detecção temporal (Onda 1 vs Onda 2) classificou o tenant como `fadiga_detectada`, com `fatigueZScore`, `fatiguePValue` e `fatigueReason` anexados.
- **Ranking de canais/formatos por CVR dentro do tenant:** cada tenant aparece com seus próprios canais e formatos, ordenados por conversão.

**Regras de isolamento:** o agrupamento é feito exclusivamente a partir dos slots próprios de cada tenant, e o comparativo A/B é calculado apenas sobre campanhas do próprio tenant. Não há junção cruzada nem medição agregada entre tenants distintos.

#### 8.6.3 Consumo no calendário e no portal de revisão

- `campaign_calendar.py` anexa aos slots os campos `fatigueStatus`, `fatigueZScore`, `fatiguePValue`, `fatigueDetected` e `fatigueReason` e acrescenta o alerta de fadiga à justificativa do `hookRecomendadoJustificativa`, sem mutar a campanha (datas, canais, UTM e cópia permanecem intocados).
- `review_dashboard.py --build --utm-report <relatorio.json>` expõe `hookBenchmarks.byTenant` no `portal-data.json` e renderiza o indicador "Fadiga de Hook" no painel de métricas do portal, com o número de tenants com fadiga detectada.

### 8.7 Fluxo assistido de promoção de vencedores (`promote-hook`)

A Etapa 10 adiciona o subcomando `promote-hook` a `tools/approval_cli.py`, que pontua a recomendação estatística do relatório UTM (`rankings.hookComparison.byCampaign`) à atualização do manifesto da campanha (`tenants/<tenantId>/campaigns/<slug>.json`) com um histórico de auditoria (`promotionHistory`). É um fluxo humano-em-ciclo: nada é publicado nem alterado sem `--apply`, e mesmo com `--apply` há um gate de qualidade editorial antes de gravar.

**CLI:**
```bash
python tools/approval_cli.py promote-hook \
  --tenant <tenantId> --campaign <slug> \
  --utm-report <caminho/utm-performance-report.json> \
  --reviewer "<nome>" \
  [--dry-run | --apply]
```

- **`--dry-run` (padrão):** só exibe o preview (diff `difflib.unified_diff` contra o manifesto) e o alerta de fadiga, sem gravar nada. `applied=false`.
- **`--apply`:** grava a entrada `promotionHistory` no arquivo de aprovações do titular (`.workspace/tmp/aprovacoes-titular.json`) de forma atômica (arquivo `.tmp` + `os.replace`), sem sobra de temporários.

**Requisitos de segurança (todos obrigatórios):**

1. **Significância estatística:** o comparativo da campanha deve ter `classification` em `vencedor_A` ou `vencedor_B`, `|z| >= 1,96` e `p < 0,05` (95% de confiança). Caso contrário, aborta com `PROMOTION_NAO_SIGNIFICATIVO` e nada grava.
2. **Isolamento multi-tenant:** o `tenantId` da linha de comparativo deve ser exatamente o tenant solicitado. Mesmo slug de campanha pertencente a outro tenant é rejeitado com `PROMOTION_TENANT_DIVERGENTE`.
3. **Alerta de fadiga:** quando `tenantBenchmarks` indica `hooksComFadiga=true` para o tenant, o preview exibe o alerta proeminente (`fatigueDetected`, `fatigueStatus`, `fatigueReason`) antes do diff.
4. **Gate editorial (`--apply` apenas):** executa `editorial_qa --all --strict` antes de gravar. Qualquer erro ou aviso aborta com `PROMOTION_EDITORIAL_QA_REPROVADA` e sem escrita parcial.
5. **Portabilidade:** todos os caminhos (relatório UTM, arquivo de aprovações) são validados para ficarem dentro da raiz do checkout (`git rev-parse --show-toplevel`); temporários ficam somente em `.workspace/`.

**Entrada de auditoria (`promotionHistory`):**
Cada promoção persistida acrescenta um item com:
- `campaignId`, `tenantId`, `promotedVariant` (`A` ou `B`),
- `zScore`, `pValue`, `classificationReason`,
- `fatigueStatus`, `fatigueDetected`,
- `sourceReport` (caminho do relatório UTM usado),
- `promotedAt` (ISO-8601 UTC),
- `promotedBy` (revisor).

O portal de revisão (`review_dashboard.py --build`) expõe `promotionHistory` por campanha no `portal-data.json` e o renderiza no card da campanha (variante, revisor, data, z/p, fadiga e fonte), mantendo o histórico completo de promoções visível ao titular.

**Consumo no calendário:** `campaign_calendar.py` continua a anexar `hookRecomendado`/`hookRecomendadoJustificativa` aos slots como recomendação apenas; a decisão de trocar o hook e a gravação da promoção continuam sendo do titular via `promote-hook --apply`.

---

### 8.8 Reconciliação pós-publicação e atribuição de pacotes (`bundleAttribution`)

A Etapa 12 fecha o ciclo de atribuição (closed-loop attribution) conectando os pacotes entregues pelo `publish_bundler` (manifestos `*-manifest.json` em `.workspace/bundles/<tenantId>/<slug>/`) aos dados de performance UTM do `utm_report_importer`, produzindo um `bundleAttribution` persistido em `.workspace/tmp/utm-report/bundle-attribution.json`. É uma leitura complementar: nunca modifica `.zip` nem manifesto entregue (somente leitura), e `autoPublish: false` permanece preservado — a publicação continua estritamente manual.

**CLI:**
```bash
python tools/utm_report_importer.py --reconcile-bundles [--json] \
  [--root <raiz>] [--bundles-dir <dir>] [--utm-report <caminho.json>]
```

- `--reconcile-bundles`: executa a cruzamento bundle → UTM.
- `--bundles-dir`: sobrescreve o diretório padrão de bundles (`.workspace/bundles`).
- `--utm-report`: caminho do relatório UTM JSON (padrão: `.workspace/tmp/utm-report/utm-performance-report.json`). Quando omitido, descobre recursivamente um relatório `utm*.json` em `.workspace/tmp/`.
- `--json`: emite JSON no stdout.

**Estados de `bundleAttribution` (status):**

| Status | Significado |
|--------|-------------|
| `reconciliado` | Manifesto existe e o relatório UTM contém metrica para o `(tenantId, slug)` correspondente. Anexa impressões, cliques, CTR, conversões, conversionRate, observedUpliftPct e winnerSustained (quando `promotionHistory` presente). |
| `aguardando_metricas` | Bundle aprovado mas ainda sem dados de UTM (relatório ausente ou slot não encontrado para o `(tenantId, slug)`). `metrics` e `winnerSustained` são `null`. |
| `divergencia_tenant` | `tenantId` do manifesto não corresponde a nenhum tenant no relatório UTM (isolamento multi-tenant violado). |
| `não_elegível_para_PREVIA_NAO_APROVADA` | Bundle com selo `PREVIA_NAO_APROVADA` não é elegível para atribuição até aprovação expressa do titular. |

**Requisitos de segurança (todos obrigatórios):**

1. **Imutabilidade dos pacotes:** nunca modifica `.zip` nem `*-manifest.json` em `.workspace/bundles/` (somente leitura).
2. **Isolamento multi-tenant:** `tenantId` do manifesto deve bater com o tenant do slot UTM. Caso contrário, atribui `divergencia_tenant`.
3. **autoPublish: false:** preservado; a publicação continua estritamente manual (o titular aprova antes de distribuir).
4. **Portabilidade:** todos os caminhos são validados para ficarem dentro da raiz do checkout (`git rev-parse --show-toplevel`); temporários ficam somente em `.workspace/`; comportamento idêntico no Windows e Linux.

**Consumo no portal de revisão:** `review_dashboard.py --build` expõe o `bundleAttribution` por campanha no `portal-data.json` e o renderiza no card da campanha (status de atribuição, status de aprovação, SHA-256 do bundle, métricas, uplift observado e vencedor sustentado), mantendo a rastreabilidade do pacote entregue até o dado de performance.

**Consumo no calendário editorial:** `campaign_calendar.py` anexa a `bundleAttribution` aos slots quando disponível, para que o titular veja, ao mesmo tempo, a recomendação de hook e o estado de atribuição do pacote já distribuído.

---

## 9. Limites deste playbook

- Não publica, agenda nem altera posts já publicados.
- Não gera áudio, TTS nem faixa sonora (política de vídeo sem áudio do projeto).
- A simulação de tráfego é apenas prova de fio: números sintéticos, `revenueBRL` nulo,
  nenhuma transação financeira.
- Não substitui a aprovação do titular nem o Release Gate
  (`python tools/release_audit.py --strict --json`).

## 10. Referências

- [Padrão de rastreio UTM](rastreio-utm.md)
- [Arquitetura da fábrica](arquitetura-fabrica.md)
- [Guia de novo nicho](guia-novo-nicho.md)
- `tools/utm_simulator.py`, `tools/tests/test_utm_simulator.py`,
  `tools/utm_report_importer.py`, `tools/tests/test_utm_report_importer.py`,
  `tools/tests/test_bundle_attribution.py`, `tools/approval_cli.py`,
  `tools/tests/test_hook_promotion_cli.py`,
  `tools/campaign_calendar.py`, `04-legendas/matriz-utm-consolidada.csv`
