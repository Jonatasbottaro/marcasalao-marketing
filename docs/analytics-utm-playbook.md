# Playbook de Analytics & Atribuição UTM — Fábrica Multi-Tenant

> **Versão:** 1.0  
> **Data:** 2026-11-20  
> **Escopo:** 4 tenants ativos (`marca-salao`, `meu-salao`, `estudio-flow`, `multitrack-hub`) e o nicho planejado `clinica-vital`  
> **Status:** operacional em modo DRAFT; publicação continua manual e depende de aprovação do titular

Este playbook complementa [rastreio-utm.md](rastreio-utm.md). O padrão de parâmetros e a
matriz consolidada continuam sendo a fonte canônica; aqui ficam o mapa de eventos por
nicho, as receitas de configuração em GA4, Plausible e Umami, a validação pré-publicação
com `tools/utm_simulator.py` e a rotina semanal de leitura da matriz.

---

## 1. Convenções de rastreio

- URL padrão: `https://<domain-do-tenant>/?utm_source=...&utm_medium=...&utm_campaign=...&utm_content=...`
- `utm_campaign` é sempre o slug completo da campanha (`camp-...`).
- **Onda 1 (lançamento 9:16):** `utm_content=<tenantId>` (ex.: `marca-salao`).
- **Onda 2 (reaproveitamento):** `utm_content=repurpose-1x1` (Feed 1:1) e
  `utm_content=repurpose-16x9` (Vídeo 16:9).
- `utm_source`/`utm_medium` por canal: `instagram/reels`, `instagram/feed`,
  `youtube/shorts`, `youtube/video`, `facebook/reels`.
- Valores em minúsculas, sem espaços ou acentos, alfabeto `[a-z0-9._-]`.
- Domínios por tenant vêm de `tenants/<tenantId>/brand-kit.json`:

| Tenant | Domínio |
| --- | --- |
| `marca-salao` | `marcasalao.com.br` |
| `meu-salao` | `meusalao.com.br` |
| `estudio-flow` | `estudioflow.com.br` |
| `multitrack-hub` | `multitrackhub.com.br` |
| `clinica-vital` (planejado) | definir no brand-kit antes de qualquer URL |

---

## 2. Mapa de eventos de conversão por nicho

Os eventos abaixo são o catálogo validado por `tools/utm_simulator.py` em
`RECOMMENDED_EVENTS`. Criar **todos** os eventos na ferramenta de analytics antes da
primeira publicação de cada tenant; o monitoramento semanal usa exatamente estes nomes.

### 2.1 `marca-salao` — agenda online

| Etapa do funil | Evento | Onde disparar | Propriedades |
| --- | --- | --- | --- |
| Consideração | `schedule_view` | página/produto de agenda | `tenant=marca-salao`, `utm_campaign`, `utm_content` |
| Intenção | `booking_link_click` | clique no CTA de agendamento | idem |
| Conversão | `booking_started` | início do fluxo de agendamento | idem |

### 2.2 `meu-salao` — gestão de atendimentos

| Etapa do funil | Evento | Onde disparar | Propriedades |
| --- | --- | --- | --- |
| Consideração | `agenda_view` | tela de agenda | `tenant=meu-salao`, UTMs |
| Meio | `attendance_checkin` | check-in de atendimento | idem |
| Conversão | `booking_completed` | agendamento concluído | idem |

### 2.3 `estudio-flow` — estúdio de pilates/bem-estar

| Etapa do funil | Evento | Onde disparar | Propriedades |
| --- | --- | --- | --- |
| Consideração | `class_schedule_view` | grade de turmas | `tenant=estudio-flow`, UTMs |
| Conversão | `trial_class_request` | pedido de aula experimental | idem |

### 2.4 `multitrack-hub` — catálogo, stems e rateios

| Etapa do funil | Evento | Onde disparar | Propriedades |
| --- | --- | --- | --- |
| Consideração | `rateio_view` | página de rateio | `tenant=multitrack-hub`, UTMs |
| Meio | `rateio_download` | download do pacote de rateio | idem |
| Conversão | `stems_download` | download de stems | idem |

### 2.5 `clinica-vital` — clínica de saúde (nicho em onboarding)

| Etapa do funil | Evento | Onde disparar | Propriedades |
| --- | --- | --- | --- |
| Consideração | `appointment_slot_view` | visualização de horários | `tenant=clinica-vital`, UTMs |
| Conversão | `appointment_booked` | agendamento confirmado | idem |

> `clinica-vital` ainda não possui `tenants/clinica-vital/brand-kit.json` nem campanha no
> calendário. O catálogo já existe para que a configuração de eventos seja feita junto do
> onboarding; não gerar URL UTM para o nicho antes do contrato e do domínio existirem.

### 2.6 Regras comuns aos eventos

1. Nome do evento em `snake_case`, sem prefixo de canal — a comparação entre canais é
   feita por `utm_source`/`utm_medium`, não pelo nome do evento.
2. Nunca incluir dados pessoais (nome, telefone, e-mail) em propriedades de evento.
3. O evento de conversão deve ser declarado como conversão/objetivo **antes** da
   primeira coleta; retroagir métricas não é possível na maioria das ferramentas.
4. Eventos de clique em CTA do site são a fonte de aprovação; a reprodução social não
   deve ser contada como conversão.

---

## 3. Receita GA4

**Pré-requisito:** uma propriedade GA4 por domínio de tenant.

1. Admin → Data streams → Web: instalar a Google tag (`gtag.js`) no template base.
2. Confirmar que nenhum redirect descarta a query string (testar com URL da matriz).
3. Admin → Custom definitions → criar dimensão de evento:
   - Nome: `utm_content`; Escopo: Event; Parâmetro do evento: `utm_content`.
   - Repetir para `tenant` e, se necessário, `utm_campaign` (embora GA4 já exponha
     `Session campaign` nativamente).
4. Disparar eventos com os UTMs anexados ao evento:

```html
<script>
  function trackTenantEvent(name, props) {
    const q = new URLSearchParams(window.location.search);
    gtag('event', name, {
      tenant: props.tenant,
      utm_source: q.get('utm_source') || '',
      utm_medium: q.get('utm_medium') || '',
      utm_campaign: q.get('utm_campaign') || '',
      utm_content: q.get('utm_content') || '',
      ...props.extra
    });
  }
  // exemplo
  document.querySelector('#cta-agendamento')?.addEventListener('click', () => {
    trackTenantEvent('booking_link_click', { tenant: 'marca-salao' });
  });
</script>
```

5. Admin → Events: marcar `booking_started`, `booking_completed`,
   `trial_class_request`, `stems_download` e `appointment_booked` como conversões
   (por tenant, conforme o mapa da seção 2).
6. Validar em Admin → DebugView com uma URL UTM real antes de publicar.
7. Relatórios → Aquisição → Aquisição de tráfego: a sessão aparece como
   `utm_source / utm_medium`; em Explorações, usar `Session campaign` e a dimensão
   `utm_content` para comparar variantes e ondas.

---

## 4. Receita Plausible

1. Criar o site do tenant no Plausible (nuvem ou self-hosted) e inserir o script com
   `data-domain="<domínio>"` no `<head>`.
2. O Plausible captura `utm_source`, `utm_medium`, `utm_campaign` e `utm_content`
   automaticamente como propriedades de sessão.
3. Site Settings → Goals: criar uma meta de evento para cada evento do mapa da seção 2
   (`booking_link_click`, `booking_started`, `class_schedule_view`, ...).
4. Instrumentar os eventos no site:

```html
<script>
  plausible('booking_started', {
    props: { tenant: 'marca-salao', wave: 'onda-1' }
  });
</script>
```

5. Para funil (Onda 1 → Onda 2), usar Funnels com as metas já criadas e filtrar por
   `utm_content=repurpose-1x1` ou `repurpose-16x9`.
6. Top Sources → aba UTM: isolar `utm_campaign` para comparar campanhas do mesmo tenant.
7. Validar em tempo real (janela anônima) antes de publicar.

---

## 5. Receita Umami

1. Criar um website por domínio no painel Umami e inserir o script de rastreamento.
2. Website Settings → habilitar o rastreamento UTM
   (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`).
3. Instrumentar eventos:

```html
<script>
  umami.track('rateio_download', {
    tenant: 'multitrack-hub',
    utm_campaign: new URLSearchParams(location.search).get('utm_campaign') || ''
  });
</script>
```

4. Reports → Events: criar a lista de eventos do mapa da seção 2 e filtrar por
   propriedade `utm_campaign` para acompanhar uma campanha específica.
5. Validar com uma URL UTM real da matriz antes de publicar; conferir se o evento
   carrega a propriedade `tenant`.

---

## 6. Validação pré-publicação com `utm_simulator.py`

Antes de liberar qualquer slot do calendário, rodar a auditoria sobre 100% das URLs:

```bash
python tools/utm_simulator.py --json
python tools/utm_simulator.py --calendar 04-legendas/calendario-editorial.json --json
```

Comprovar o caminho sintético das duas ondas (sem cobrança financeira):

```bash
python tools/utm_simulator.py --simulate-traffic \
  --out-dir .workspace/tmp/utm-sim --json
```

O pipeline mestre executa a mesma auditoria no estágio `utm`:

```bash
python tools/factory_cli.py pipeline --all --skip-render --json
```

### 6.1 Códigos de auditoria

| Código | Severidade | Significado / ação |
| --- | --- | --- |
| `DOMINIO_DIVERGENTE` | erro | host da URL difere do `domain` do brand-kit |
| `ESQUEMA_NAO_HTTPS` | erro | URL não usa HTTPS |
| `UTM_PARAM_AUSENTE` | erro | falta `utm_source`, `utm_medium`, `utm_campaign` ou `utm_content` |
| `UTM_VALOR_NAO_PADRONIZADO` | erro | valor com maiúscula, espaço, acento ou fora de `[a-z0-9._-]` |
| `UTM_CAMPANHA_DIVERGENTE` | erro | `utm_campaign` difere do slug da campanha |
| `UTM_PARAM_DUPLICADO` | erro | parâmetro repetido na mesma URL |
| `COLISAO_CAMPANHA_ENTRE_TENANTS` | erro | mesmo `utm_campaign` em dois tenants |
| `COLISAO_ATRIBUICAO` | erro | mesmo par `utm_campaign`+`utm_content` em dois tenants |
| `TENANT_DESCONHECIDO` | erro | slot aponta para tenant sem brand-kit |
| `UTM_SOURCE_DESCONHECIDO` | aviso | origem fora do vocabulário documentado |
| `UTM_CANAL_DIVERGENTE` | aviso | par origem/mídia incomum (ex.: `youtube/feed`) |

Exit codes: `0` aprovado; `1` auditoria reprovada; `2` uso/caminho inválido.

### 6.2 Checklist antes de publicar

1. `utm_simulator.py` retorna `ok: true`.
2. `totalUrls == urlsAudited == urlsOk` e `derivedUrls` conferido (campanhas novas).
3. Nenhuma colisão entre tenants.
4. Eventos do nicho criados na ferramenta de analytics e marcados como conversão.
5. Teste de ponta a ponta em janela anônima com a URL exata do slot.
6. Slot com `autoPublish: false` e aprovação expressa do titular no portal.
7. Registro do resultado no diário da campanha (data, slot, ferramenta, evidência).

---

## 7. Leitura semanal da matriz consolidada

Fonte: `04-legendas/matriz-utm-consolidada.csv` (gerada por `tools/campaign_calendar.py`).

Colunas relevantes:

| Coluna | Uso na análise |
| --- | --- |
| `slot_id` | chave para juntar com exportações de analytics |
| `onda`, `semana`, `data_sugerida` | recorte temporal e comparação Onda 1 vs. Onda 2 |
| `tenant_id`, `slug` | segmentação por marca e campanha |
| `canal`, `formato_video` | comparação Reels/Shorts/Feed 1:1/Vídeo 16:9 |
| `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` | chaves de atribuição |
| `status_editorial`, `auto_publish` | governança; confirma que nada foi automatizado |

### 7.1 Rotina semanal (segunda-feira)

1. Exportar da ferramenta escolhida as sessões/conversões agrupadas por
   `utm_source`, `utm_medium`, `utm_campaign` e `utm_content`.
2. Juntar com a matriz por `(tenant_id, slug, utm_content)`.
3. Calcular por linha:
   - `CVR = conversões / sessões`;
   - `share_conversoes = conversões da linha / conversões do tenant`;
   - `delta_onda2 = CVR(Onda 2) - CVR(Onda 1)` por tenant.
4. Comparar canais dentro do mesmo tenant (nunca entre tenants com funis diferentes).
5. Sinalizar anomalias: slot com 0 sessões após 72h; CVR acima de 3x a mediana do
   tenant; `utm_content` inesperado no relatório (indica URL fora da matriz).
6. Registrar decisões no diário; ajustes de URL valem apenas para slots futuros.
7. Nunca editar post publicado para "corrigir" UTM: registrar a divergência e corrigir
   no próximo slot.

### 7.2 O que este playbook não faz

- Não publica, não agenda e não altera posts publicados.
- Não gera áudio, TTS ou qualquer faixa sonora (política vigente do projeto).
- Não simula receita, cobrança ou ROI financeiro; a simulação de tráfego é apenas
  prova de fio com `revenueBRL` nulo.
- Não substitui a validação do titular nem o Release Gate
  (`python tools/release_audit.py --strict --json`).

---

## 8. Referências

- [Padrão de rastreio UTM](rastreio-utm.md)
- [Arquitetura da fábrica](arquitetura-fabrica.md)
- [Guia de novo nicho](guia-novo-nicho.md)
- `tools/utm_simulator.py`, `tools/factory_cli.py`, `tools/campaign_calendar.py`