# Padrão de Rastreio UTM — Marca Salão

> **Versão:** 1.2  
> **Data:** 2026-11-18  
> **Responsável:** pendente de definição  
> **Status:** rascunho para validação do titular

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
> em registros de campanha.

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

---

## 7. Calendário editorial automatizado (tools/campaign_calendar.py)

A partir da versão 1.2, o cronograma editorial das campanhas publicáveis é gerado
por `tools/campaign_calendar.py`, que lê os tenants em `tenants/*/` e os pacotes
em `04-legendas/pacotes-publicacao/<tenantId>/<slug>/checklist-publicacao.json` e
distribui as campanhas em um cronograma intercalado:

- **Nunca duas campanhas do mesmo tenant no mesmo dia** (regra dura, validada
  por teste automatizado).
- Até 2 campanhas por dia; cada campanha cobre os 3 canais (Instagram Reels,
  YouTube Shorts, Facebook Reels) — 8 campanhas × 3 canais = 24 slots.
- Cada slot recebe janela de horário sugerida, política de áudio do tenant
  (`-an` para estudio-flow, marca-salao e meu-salao; faixa própria para
  multitrack-hub) e a URL UTM da matriz da seção 6.
- Todo texto gerado é auditado por tenant com
  `tenant_validator.validate_text_against_guardrails(...)`; qualquer violação
  aborta antes de gravar.
- `statusEditorial: "aguardando_aprovacao_titular"` e `autoPublish: false` em
  todos os slots: publicação 100% manual e condicionada à aprovação do titular.

### CLI

```text
# Cronograma a partir de uma data (ISO YYYY-MM-DD)
python tools/campaign_calendar.py --start-date 2026-11-23

# Saída JSON com hashes SHA-256 dos arquivos gerados
python tools/campaign_calendar.py --start-date 2026-11-23 --json
```

### Saídas

- `04-legendas/calendario-editorial.json`: 24 slots estruturados (`slotId`,
  `dataSugerida`, `janelaHorario`, `tenantId`, `brandName`, `slug`, `canal`,
  `formato`, `audioPolicy`, `utmUrl`, `statusEditorial`, `autoPublish`).
- `04-legendas/calendario-editorial.md`: cronograma visual para operação manual,
  checklist pré-publicação (incluindo o lembrete de locução externa para os
  tenants `-an`) e a matriz UTM consolidada.

### Cronograma vigente (gerado em 2026-11-18, início 2026-11-23)

| Data | Campanhas do dia | Tenants |
|------|------------------|---------|
| 2026-11-23 | camp-shorts-completo-multitrack-001; camp-saas-demo-marca-salao-001 | multitrack-hub, marca-salao |
| 2026-11-24 | camp-saas-demo-meu-salao-001; camp-shorts-rateios-002 | meu-salao, multitrack-hub |
| 2026-11-25 | camp-saas-demo-estudio-flow-001; camp-saas-demo-ns001-agenda-001 | estudio-flow, marca-salao |
| 2026-11-26 | camp-saas-demo-meu-salao-002; camp-shorts-stems-workflow-003 | meu-salao, multitrack-hub |

> A fonte da verdade é `04-legendas/calendario-editorial.json`; regenerar com
> outra data inicial substitui o cronograma vigente.

---

## 8. Histórico

| Data       | Autor       | Alteração |
|------------|-------------|-----------|
| 2026-11-18 | Agente — codex/fase1-conformidade-editorial | Criação do padrão inicial |
| 2026-11-18 | Agente 3 — codex/etapa3-agente3-publish-utm | Geração automatizada de URLs via tools/publish_pack.py e tabela de URLs por canal/tenant |
| 2026-11-18 | Agente 3 — codex/etapa4-agente3-calendario-utm | Calendário editorial automatizado (campaign_calendar.py), matriz UTM consolidada de 8 campanhas × 3 canais (24 URLs) e passo a passo de analytics (GA4/Plausible/Umami) |
