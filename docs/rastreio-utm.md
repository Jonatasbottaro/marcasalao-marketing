# Padrão de Rastreio UTM — Marca Salão

> **Versão:** 1.4  
> **Data:** 2026-11-21  
> **Responsável:** titular (D2 em aberto)  
> **Status:** rascunho para validação do titular — 3 decisões pendentes, consolidadas em [checklist-decisoes-titular.md](checklist-decisoes-titular.md)

---

## 1. Objetivo

Definir o padrão oficial de parâmetros UTM para campanhas do Marca Salão, garantindo
rastreabilidade consistente nos canais Instagram, Facebook e qualquer outro canal com
link rastreável.

## 2. Padrão de parâmetros

| Parâmetro       | Obrigatório | Valores aceitos / padrão                               | Notas |
|----------------|-------------|--------------------------------------------------------|-------|
| `utm_source`    | Sim         | `instagram`, `facebook`, `youtube`, `tiktok`, `linktree` | Plataforma de origem |
| `utm_medium`    | Sim         | `reels`, `stories`, `feed`, `shorts`, `bio`            | Formato/posicionamento |
| `utm_campaign`  | Sim         | `ns-001`, `ns-002` (ver seção 3)                       | Código da campanha |
| `utm_content`   | Recomendado | `h01`, `h15`, `v01`, `v02` etc.                        | Variante de arte ou hook |
| `utm_term`      | Opcional    | livre                                                   | Palavra-chave paga, se aplicável |

### Formato padrão de URL

```
https://marcasalao.com.br/?utm_source=FONTE&utm_medium=FORMATO&utm_campaign=CAMPANHA&utm_content=VARIANTE
```

### Exemplos prontos

```
# NS-001 — Agenda — Reels Instagram
https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=ns-001&utm_content=h15

# NS-001 — Agenda — Stories Instagram
https://marcasalao.com.br/?utm_source=instagram&utm_medium=stories&utm_campaign=ns-001&utm_content=h15

# NS-001 — Agenda — Feed Facebook
https://marcasalao.com.br/?utm_source=facebook&utm_medium=feed&utm_campaign=ns-001&utm_content=h15

# NS-002 — Agendamento online — Reels Instagram
https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=ns-002&utm_content=h01

# NS-002 — Agendamento online — Stories Instagram
https://marcasalao.com.br/?utm_source=instagram&utm_medium=stories&utm_campaign=ns-002&utm_content=h01
```

> [!IMPORTANT]
> As URLs acima são modelos. Validar que o domínio `marcasalao.com.br` resolve corretamente
> e que os parâmetros chegam à ferramenta de analytics antes de usar em produção.

### Convenção multi-tenant (Etapa 4)

A partir da Etapa 4, o mesmo padrão de parâmetros vale para os 4 tenants da
content factory, cada um com seu próprio domínio de destino:

| Tenant | Marca | Domínio oficial | Nicho |
|--------|-------|------------------|-------|
| `marca-salao` | Marca Salão | `marcasalao.com.br` | SaaS de gestão para salões |
| `meu-salao` | Meu Salão | `meusalao.com.br` | SaaS de agenda para salões |
| `estudio-flow` | Estúdio Flow | `estudioflow.com.br` | Aulas e turmas em estúdio (pilates/bem-estar) |
| `multitrack-hub` | Multitrack Hub | `multitrackhub.com.br` | Catálogo de multitracks, stems e rateios |

Regras multi-tenant:

1. `utm_campaign` é sempre o slug completo da campanha
   (ex.: `camp-saas-demo-marca-salao-001`), igual ao `slug` da entrega em
   `02-reels-shorts/deliveries/<tenantId>/<slug>/`.
2. `utm_content` identifica a variante/posicionamento, nunca a marca:
   - **Onda 1 (lançamento 9:16):** `utm_content=<tenantId>` (ex.: `marca-salao`),
     igual em todos os canais da campanha.
   - **Onda 2 (reaproveitamento):** `utm_content=repurpose-1x1` para Instagram
     Feed 1:1 e `utm_content=repurpose-16x9` para YouTube Vídeo 16:9.
3. `utm_source`/`utm_medium` por canal: `instagram`/`reels`, `youtube`/`shorts`,
   `facebook`/`reels` na Onda 1; `instagram`/`feed` e `youtube`/`video` na Onda 2.
4. A URL de um tenant nunca aponta para o domínio de outro tenant; o domínio vem
   do `brand-kit.json` de cada tenant e é auditado junto com o texto da legenda.
5. Multitrack Hub com tema rateios continua direcionando para
   `https://multitrackhub.com.br/rateios` quando o slot pedir a seção
   específica; a URL rastreada padrão continua sendo a home com UTMs.

---

## 3. Dicionário de campanhas

| Código       | Nome completo                              | Status     |
|-------------|---------------------------------------------|------------|
| `ns-001`    | Organização e visibilidade da agenda        | rascunho   |
| `ns-002`    | Agendamento online no Marca Salão           | rascunho   |

> Adicionar novos códigos de campanha nesta tabela ao criar o briefing.

---

## 4. Regras editoriais

1. **Link na bio (Instagram):** usar `utm_medium=bio` somente quando o link rastreado for o link fixo da bio, não um link em legenda.
2. **Stories com sticker:** `utm_medium=stories`. O sticker precisa ser autorizado antes do uso; não inferir que botão desenhado na arte cria sticker rastreado.
3. **Facebook:** usar URL completa na legenda com os parâmetros UTM. Indicar "Acesse pelo link da descrição".
4. **Rastreamento ainda não configurado:** enquanto a ferramenta de analytics não estiver definida e validada, incluir a marcação `<!-- rastreamento: NÃO CONFIGURADO -->` nos registros de campanha e não publicar links UTM como definitivos.
5. **Não alterar parâmetros UTM de posts já publicados:** qualquer mudança invalida o histórico de dados.

---

## 5. Ferramenta de analytics

- **Ferramenta definida:** [PENDENTE — inserir link ou nome da ferramenta oficial]
- **Acesso:** [PENDENTE — inserir responsável e nível de acesso]
- **Dashboard de campanha:** [PENDENTE — inserir link do relatório oficial]

### 5.1 Passo a passo de configuração (antes da primeira publicação)

A escolha da ferramenta é decisão do titular. Os passos abaixo valem para os três
candidatos avaliados (GA4, Plausible, Umami) e devem ser executados **por domínio
de tenant** (`marcasalao.com.br`, `meusalao.com.br`, `estudioflow.com.br`,
`multitrackhub.com.br`) antes da primeira publicação com link rastreado.

**Opção A — GA4 (Google Analytics 4)**

1. Criar uma propriedade GA4 por domínio em analytics.google.com.
2. Instalar a Google tag (gtag.js) em todas as páginas do site, no template base.
3. Confirmar que a página de destino preserva a query string UTM — nenhum
   redirect pode descartar os parâmetros `utm_*`.
4. Verificar o relatório de aquisição (fontes de tráfego / origem e mídia):
   `utm_source` / `utm_medium` devem aparecer como origem/mídia da sessão.
5. Teste de ponta a ponta: abrir uma URL da matriz da seção 6 em janela limpa
   de navegador, navegar ao menos uma página e conferir a sessão no relatório
   em tempo real.
6. Registrar nesta seção o acesso e o link do relatório oficial.

**Opção B — Plausible**

1. Criar o site no Plausible (nuvem em plausible.io) ou em instância self-hosted.
2. Inserir o script do Plausible (`script.js` com `data-domain`) no `<head>` de
   todas as páginas.
3. Os parâmetros UTM são capturados automaticamente como propriedades (source,
   medium, campaign, content), visíveis em Top Sources e nos filtros UTM.
4. Teste de ponta a ponta igual ao da Opção A, conferindo o painel em tempo real.
5. Registrar nesta seção o acesso e o link do painel.

**Opção C — Umami**

1. Criar a instância na nuvem (umami.is) ou self-hosted (Docker).
2. Adicionar o website no painel e inserir o script de rastreamento no `<head>`.
3. Ativar o rastreamento UTM nas configurações do website (utm_source,
   utm_medium, utm_campaign, utm_content).
4. Teste de ponta a ponta igual ao da Opção A, conferindo a visão de UTM nos
   relatórios do website.
5. Registrar nesta seção o acesso e o link do painel.

**Checklist comum às três opções**

1. A ferramenta deve ser escolhida e validada pelo titular antes da primeira
   publicação com link rastreado.
2. Sem analytics validado, manter a marcação `<!-- rastreamento: NÃO CONFIGURADO -->`
   (regra 4 da seção 4) e não declarar links UTM como ativos.
3. Não alterar parâmetros UTM de posts já publicados (regra 5 da seção 4).

> [!NOTE]
> Esta seção deve ser preenchida antes das primeiras publicações com link rastreado.
> Enquanto estiver como PENDENTE, nenhum link UTM deve ser declarado como ativo
> em registros de campanha. Os critérios que autorizam remover a marcação
> `<!-- rastreamento: NÃO CONFIGURADO -->` estão na seção 9 e no
> [checklist de decisões do titular](checklist-decisoes-titular.md).

### 5.2 Guia de leitura dos UTMs (antes da primeira publicação)

Como conferir, em cada ferramenta, que os parâmetros da matriz estão chegando
corretamente — executar uma vez com uma URL de teste antes da primeira
publicação real:

**GA4**

1. Relatórios → Aquisição de tráfego → "Origem/mídia": cada sessão rastreada
   aparece como `utm_source / utm_medium` (ex.: `instagram / reels`,
   `youtube / video`).
2. Para ver `utm_campaign`: explorar a dimensão "Campanha de sessão" ou usar
   Explorações → dimensão "Session campaign".
3. Para ver `utm_content` (variante A/B de hook): Explorações → dimensão
   "Session manual content" — é nela que se compara o desempenho entre
   `repurpose-1x1` e `repurpose-16x9`, por exemplo.
4. Teste: abrir uma URL da matriz em janela anônima, navegar uma página e
   conferir em Relatórios → Tempo real.

**Plausible**

1. Painel do site → Top Sources mostra `utm_source` agregado; clicar em
   "UTM" na barra de fontes abre a visão por `utm_source`, `utm_medium`,
   `utm_campaign` e `utm_content`.
2. Filtrar por `utm_campaign=camp-saas-demo-marca-salao-001` para isolar uma
   campanha; comparar `utm_content` para medir variantes.
3. Teste: mesmo fluxo de janela anônima; o evento aparece em tempo real no
   painel com os UTMs da sessão.

**Umami**

1. Painel do website → Referrers mostra a origem; com UTM habilitado
   (seção 5.1, Opção C), os eventos carregam `utm_source`, `utm_medium`,
   `utm_campaign` e `utm_content` como propriedades.
2. Usar a visão de eventos filtrando por propriedade `utm_campaign` para
   acompanhar uma campanha específica.
3. Teste: janela anônima + conferência em tempo real, igual às outras opções.

**Conversão (comum às três ferramentas)**

1. Definir o evento/objetivo de conversão antes da primeira publicação
   (ex.: visita à página de agendamento, clique em CTA do site).
2. Nomear a conversão por tenant, não por canal: a comparação entre canais
   (Instagram vs. YouTube vs. Facebook) é feita por `utm_source/utm_medium`
   dentro da mesma conversão.
3. Só declarar uma conversão como medida após validar o evento de ponta a
   ponta com uma URL UTM real da matriz.

---

## 6. Geração automatizada de URLs (tools/publish_pack.py)

A partir da versão 1.1, as URLs rastreadas são geradas automaticamente pelo
script `tools/publish_pack.py`, que lê cada entrega renderizada em
`02-reels-shorts/deliveries/<tenantId>/<slug>/` (manifest.json, .srt,
_narracao.txt), o `brand-kit.json` (`domain`, `utmDefaults`) e o
`guardrails.json` do respectivo tenant, e produz pacotes em
`04-legendas/pacotes-publicacao/<tenantId>/<slug>/`:

- `instagram-reels.md`: legenda otimizada com `utm_source=instagram`,
  `utm_medium=reels`, CTA "Conheça o sistema — link na bio" e hashtags.
- `youtube-shorts.md`: título SEO, descrição com capítulos derivados do .srt
  e `utm_source=youtube`, `utm_medium=shorts`.
- `facebook-reels.md`: copy adaptada com `utm_source=facebook`,
  `utm_medium=reels` e "Acesse pelo link da descrição".
- `checklist-publicacao.json`: metadados estruturados (hashes SHA-256 dos
  arquivos de mídia, status de aprovação dos guardrails,
  `"autoPublish": false`).

### CLI

```text
# Todas as entregas existentes
python tools/publish_pack.py --all

# Uma entrega especifica
python tools/publish_pack.py --tenant marca-salao --slug camp-saas-demo-marca-salao-001
```

Todas as cópias de legenda geradas são auditadas com
`tenant_validator.validate_text_against_guardrails(...)` antes de gravar: se
qualquer palavra proibida de `forbiddenClaims`/`forbiddenUiElements` aparecer,
o script aborta e não grava o pacote parcial.

### Tabela consolidada de URLs (8 campanhas × 3 canais = 24 URLs)

| Tenant | Campanha (slug) | Canal | URL rastreada |
|--------|-----------------|-------|---------------|
| estudio-flow | camp-saas-demo-estudio-flow-001 | Instagram Reels | https://estudioflow.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=estudio-flow |
| estudio-flow | camp-saas-demo-estudio-flow-001 | YouTube Shorts | https://estudioflow.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=estudio-flow |
| estudio-flow | camp-saas-demo-estudio-flow-001 | Facebook Reels | https://estudioflow.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=estudio-flow |
| marca-salao | camp-saas-demo-marca-salao-001 | Instagram Reels | https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | camp-saas-demo-marca-salao-001 | YouTube Shorts | https://marcasalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | camp-saas-demo-marca-salao-001 | Facebook Reels | https://marcasalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | camp-saas-demo-ns001-agenda-001 | Instagram Reels | https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-ns001-agenda-001&utm_content=marca-salao |
| marca-salao | camp-saas-demo-ns001-agenda-001 | YouTube Shorts | https://marcasalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-ns001-agenda-001&utm_content=marca-salao |
| marca-salao | camp-saas-demo-ns001-agenda-001 | Facebook Reels | https://marcasalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-ns001-agenda-001&utm_content=marca-salao |
| meu-salao | camp-saas-demo-meu-salao-001 | Instagram Reels | https://meusalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | camp-saas-demo-meu-salao-001 | YouTube Shorts | https://meusalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | camp-saas-demo-meu-salao-001 | Facebook Reels | https://meusalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | camp-saas-demo-meu-salao-002 | Instagram Reels | https://meusalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-002&utm_content=meu-salao |
| meu-salao | camp-saas-demo-meu-salao-002 | YouTube Shorts | https://meusalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-meu-salao-002&utm_content=meu-salao |
| meu-salao | camp-saas-demo-meu-salao-002 | Facebook Reels | https://meusalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-002&utm_content=meu-salao |
| multitrack-hub | camp-shorts-completo-multitrack-001 | Instagram Reels | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-completo-multitrack-001 | YouTube Shorts | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-completo-multitrack-001 | Facebook Reels | https://multitrackhub.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-rateios-002 | Instagram Reels | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-shorts-rateios-002&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-rateios-002 | YouTube Shorts | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-shorts-rateios-002&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-rateios-002 | Facebook Reels | https://multitrackhub.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-shorts-rateios-002&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-stems-workflow-003 | Instagram Reels | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-shorts-stems-workflow-003&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-stems-workflow-003 | YouTube Shorts | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-shorts-stems-workflow-003&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-stems-workflow-003 | Facebook Reels | https://multitrackhub.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-shorts-stems-workflow-003&utm_content=multitrack-hub |

> [!IMPORTANT]
> Enquanto a ferramenta de analytics (seção 5) estiver como PENDENTE, nenhum
> link UTM acima deve ser declarado como ativo em registros de campanha.

### 6.1 Matriz de reaproveitamento — Onda 2 (Feed 1:1 e Vídeo 16:9)

A Onda 2 do calendário editorial (seção 7) reaproveita cada uma das 8 campanhas
em UM slot adicional, alternando Instagram Feed 1:1 e YouTube Vídeo 16:9. O
`utm_content` muda para identificar o derivado (`repurpose-1x1` / `repurpose-16x9`)
e o `utm_medium` acompanha o formato (`feed` / `video`):

| Tenant | Campanha (slug) | Canal | Formato | URL rastreada |
|--------|-----------------|-------|---------|---------------|
| estudio-flow | camp-saas-demo-estudio-flow-001 | Instagram Feed | 1:1 | https://estudioflow.com.br/?utm_source=instagram&utm_medium=feed&utm_campaign=camp-saas-demo-estudio-flow-001&utm_content=repurpose-1x1 |
| marca-salao | camp-saas-demo-marca-salao-001 | YouTube Vídeo | 16:9 | https://marcasalao.com.br/?utm_source=youtube&utm_medium=video&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=repurpose-16x9 |
| marca-salao | camp-saas-demo-ns001-agenda-001 | Instagram Feed | 1:1 | https://marcasalao.com.br/?utm_source=instagram&utm_medium=feed&utm_campaign=camp-saas-demo-ns001-agenda-001&utm_content=repurpose-1x1 |
| meu-salao | camp-saas-demo-meu-salao-001 | Instagram Feed | 1:1 | https://meusalao.com.br/?utm_source=instagram&utm_medium=feed&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=repurpose-1x1 |
| meu-salao | camp-saas-demo-meu-salao-002 | YouTube Vídeo | 16:9 | https://meusalao.com.br/?utm_source=youtube&utm_medium=video&utm_campaign=camp-saas-demo-meu-salao-002&utm_content=repurpose-16x9 |
| multitrack-hub | camp-shorts-completo-multitrack-001 | YouTube Vídeo | 16:9 | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=video&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=repurpose-16x9 |
| multitrack-hub | camp-shorts-rateios-002 | Instagram Feed | 1:1 | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=feed&utm_campaign=camp-shorts-rateios-002&utm_content=repurpose-1x1 |
| multitrack-hub | camp-shorts-stems-workflow-003 | YouTube Vídeo | 16:9 | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=video&utm_campaign=camp-shorts-stems-workflow-003&utm_content=repurpose-16x9 |

Combinando a tabela da seção 6 (24 URLs de lançamento) com esta (8 URLs de
reaproveitamento), a matriz completa soma **32 URLs rastreadas** — exatamente os
32 slots do calendário editorial, exportadas linha a linha em
`04-legendas/matriz-utm-consolidada.csv`.

> [!IMPORTANT]
> A mesma regra da seção 6 vale aqui: enquanto a ferramenta de analytics
> (seção 5) estiver como PENDENTE, nenhum link UTM desta tabela deve ser
> declarado como ativo em registros de campanha.

---

## 7. Calendário editorial automatizado (tools/campaign_calendar.py)

A partir da versão 1.3, o cronograma editorial das campanhas publicáveis é gerado
por `tools/campaign_calendar.py`, que lê os tenants em `tenants/*/` (brand-kit +
guardrails) e os pacotes em `04-legendas/pacotes-publicacao/<tenantId>/<slug>/`
(checklist-publicacao.json e legendas por canal) e distribui as 8 campanhas em
4 semanas, em duas ondas:

**Onda 1 — lançamento (semanas 1-2, 24 slots 9:16)**

- Cada campanha cobre os 3 canais (YouTube Shorts, Instagram Reels, Facebook
  Reels) — 8 campanhas × 3 canais = 24 slots.
- Janelas fixas por canal (BRT): YouTube 12:00-13:00, Instagram 18:30-19:30,
  Facebook 20:00-21:00.
- Regras duras, validadas por testes automatizados:
  1. Nunca duas publicações do mesmo tenant no mesmo dia.
  2. A mesma campanha nunca aparece em dois canais com menos de 48 horas de
     intervalo (ordem interna youtube → instagram → facebook, com offsets
     +0/+2/+4 dias entre canais).
  3. Semanas de segunda a sábado; domingo nunca recebe publicação.
- Cada slot recebe a política de áudio do tenant (`-an` para estudio-flow,
  marca-salao e meu-salao; faixa própria para multitrack-hub) e a URL UTM da
  matriz da seção 6.

**Onda 2 — reaproveitamento (semanas 3-4, 8 slots 1:1/16:9)**

- 1 slot adicional por campanha, alternando Instagram Feed 1:1 e YouTube
  Vídeo 16:9, com `utm_content` `repurpose-1x1` / `repurpose-16x9`
  (seção 6.1) e a mídia derivada correspondente (`<slug>-1x1.mp4` /
  `<slug>-16x9.mp4`).
- Zero colisão de tenant-dia também na Onda 2.

**Hooks A/B e auditoria**

- Cada slot carrega duas variantes de abertura: `hookVarianteA` (abertura
  original da legenda do canal no pacote) e `hookVarianteB` (abertura
  alternativa de clareza operacional, por nicho).
- Todo texto gerado (hooks A/B, títulos, notas operacionais e URLs UTM) é
  auditado por tenant com `tenant_validator.validate_text_against_guardrails(...)`;
  qualquer violação aborta antes de gravar qualquer arquivo.
- `statusEditorial: "aguardando_aprovacao_titular"` e `autoPublish: false` em
  todos os slots: publicação 100% manual e condicionada à aprovação expressa
  do titular.

### CLI

```text
# Cronograma de 4 semanas a partir de uma data (ISO YYYY-MM-DD)
python tools/campaign_calendar.py --start-date 2026-11-23 --weeks 4

# Saída JSON com hashes SHA-256 dos arquivos gerados
python tools/campaign_calendar.py --start-date 2026-11-23 --weeks 4 --json
```

### Saídas

- `04-legendas/calendario-editorial.json`: 32 slots estruturados (`slotId`,
  `onda`, `semana`, `dataSugerida`, `diaSemana`, `janelaHorarioBrt`,
  `tenantId`, `brandName`, `slug`, `preset`, `audioPolicy`, `canal`,
  `formatoVideo`, `hookVarianteA`, `hookVarianteB`, `utmParams`, `utmUrl`,
  `checklistPrePublicacao`, `statusEditorial`, `autoPublish`) mais
  metadados consolidados, regras aplicadas e métricas por tenant/canal.
- `04-legendas/calendario-editorial.md`: resumo executivo por tenant e por
  canal, cronograma visual das 4 semanas, checklist de operação manual
  pré-publicação (incluindo o lembrete de locução externa para os tenants
  `-an` e a confirmação de analytics ativa) e a tabela de URLs UTM por campanha.
- `04-legendas/matriz-utm-consolidada.csv`: 32 linhas com 20 colunas
  padronizadas (`slot_id` a `auto_publish`), UTF-8 com fim de linha LF, pronta
  para Google Sheets/Excel/Looker Studio.

### Cronograma vigente (gerado em 2026-11-19, início 2026-11-23, 4 semanas)

| Semana | Período | Onda | Slots | Conteúdo |
|--------|---------|------|-------|----------|
| 1 | 2026-11-23 a 2026-11-28 | 1 | 12 | Lançamentos 9:16 (YouTube Shorts, Instagram Reels, Facebook Reels) |
| 2 | 2026-11-30 a 2026-12-05 | 1 | 12 | Lançamentos 9:16 (YouTube Shorts, Instagram Reels, Facebook Reels) |
| 3 | 2026-12-07 a 2026-12-12 | 2 | 6 | Reaproveitamentos 1:1 / 16:9 |
| 4 | 2026-12-14 a 2026-12-15 | 2 | 2 | Reaproveitamentos 1:1 / 16:9 |

> A fonte da verdade é `04-legendas/calendario-editorial.json`; regenerar com
> outra data inicial substitui o cronograma vigente.

---

## 8. Histórico

| Data       | Autor       | Alteração |
|------------|-------------|-----------|
| 2026-11-18 | Agente — codex/fase1-conformidade-editorial | Criação do padrão inicial |
| 2026-11-18 | Agente 3 — codex/etapa3-agente3-publish-utm | Geração automatizada de URLs via tools/publish_pack.py e tabela de URLs por canal/tenant |
| 2026-11-18 | Agente 3 — codex/etapa4-agente3-calendario-utm | Calendário editorial automatizado (campaign_calendar.py), matriz UTM consolidada de 8 campanhas × 3 canais (24 URLs) e passo a passo de analytics (GA4/Plausible/Umami) |
| 2026-11-19 | Agente 3 — codex/etapa4-agente3-calendario-utm | Calendário v2 (4 semanas, 32 slots em 2 ondas, hooks A/B, matriz-utm-consolidada.csv), convenção multi-tenant da seção 2, matriz de reaproveitamento da seção 6.1 e guia de leitura dos UTMs (seção 5.2) |
| 2026-11-21 | Arquitetura de Documentação | Seção 9 com as 3 decisões pendentes do titular e os critérios de ativação dos links UTM; vínculo com o checklist de decisões |

---

## 9. Decisões pendentes do titular e ativação dos links UTM

As três decisões abaixo só podem ser tomadas pelo titular e **bloqueiam a primeira publicação manual**. O detalhe operacional (opções, evidência e registro) está em [checklist-decisoes-titular.md](checklist-decisoes-titular.md).

| ID | Decisão | Impacto direto neste padrão |
| --- | --- | --- |
| **D1** | Identidade visual externa (`Salao02`): atualizar para "Marca Salão" na origem **ou** manter overlay nas capturas | Define se a captura já sai com a marca correta ou se o `headerOverlay` continua responsável por substituir "Meu Salão". Não altera os UTMs. |
| **D2** | Ferramenta oficial de analytics (GA4 / Plausible / Umami) | Preenche a seção 5 e permite declarar as URLs das seções 6 e 6.1 como ativas. |
| **D3** | Validação final de roteiros, fixtures e link da bio `@marcasalao` | Confere a copy e o destino antes de publicar; o link da bio precisa ser conferido no perfil, não apenas citado na biografia. |

### 9.1 Critérios para ativar os links UTM (todos obrigatórios)

1. **D2 decidida:** ferramenta, responsável pelo acesso e link do relatório oficial registrados na seção 5.
2. **Domínio validado:** cada URL da matriz resolve em HTTPS no `domain` do brand-kit do tenant, sem `www` e sem redirect que perca a query.
3. **Evento de conversão criado antes da coleta**, por tenant, conforme o catálogo de [analytics-utm-playbook.md](analytics-utm-playbook.md).
4. **Teste de ponta a ponta** em janela anônima com uma URL real da matriz, confirmando os quatro parâmetros na ferramenta.
5. **Auditoria limpa:** `python tools/utm_simulator.py --json` com `ok: true`, `collisions: []` e `totalUrls == urlsAudited == urlsOk`.
6. **Publicação manual autorizada:** campanha aprovada no portal/CLI, `autoPublish: false` conferido no handoff e `release_audit --strict` aprovando 7/7.

Enquanto qualquer critério faltar, mantém-se a marcação `<!-- rastreamento: NÃO CONFIGURADO -->` e nenhuma URL desta tabela é declarada como ativa. Ajustes de UTM valem somente para slots futuros: **nunca editar post publicado para "corrigir" parâmetro**.

### 9.2 Verificação única recomendada

```bash
python tools/utm_simulator.py --json
python tools/editorial_qa.py --all --strict --json
python tools/release_audit.py --strict --json
python -m unittest discover -s tests/e2e -v
```
