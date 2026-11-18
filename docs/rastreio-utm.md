# Padrão de Rastreio UTM — Marca Salão

> **Versão:** 1.0  
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

### Tabela de URLs geradas (2026-11-18)

| Tenant | Campanha (slug) | Canal | URL rastreada |
|--------|-----------------|-------|---------------|
| marca-salao | camp-saas-demo-marca-salao-001 | Instagram Reels | https://marcasalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | camp-saas-demo-marca-salao-001 | YouTube Shorts | https://marcasalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| marca-salao | camp-saas-demo-marca-salao-001 | Facebook Reels | https://marcasalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-marca-salao-001&utm_content=marca-salao |
| meu-salao | camp-saas-demo-meu-salao-001 | Instagram Reels | https://meusalao.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | camp-saas-demo-meu-salao-001 | YouTube Shorts | https://meusalao.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| meu-salao | camp-saas-demo-meu-salao-001 | Facebook Reels | https://meusalao.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-saas-demo-meu-salao-001&utm_content=meu-salao |
| multitrack-hub | camp-shorts-completo-multitrack-001 | Instagram Reels | https://multitrackhub.com.br/?utm_source=instagram&utm_medium=reels&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-completo-multitrack-001 | YouTube Shorts | https://multitrackhub.com.br/?utm_source=youtube&utm_medium=shorts&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |
| multitrack-hub | camp-shorts-completo-multitrack-001 | Facebook Reels | https://multitrackhub.com.br/?utm_source=facebook&utm_medium=reels&utm_campaign=camp-shorts-completo-multitrack-001&utm_content=multitrack-hub |

> [!IMPORTANT]
> Enquanto a ferramenta de analytics (seção 5) estiver como PENDENTE, nenhum
> link UTM acima deve ser declarado como ativo em registros de campanha.

---

## 7. Histórico

| Data       | Autor       | Alteração |
|------------|-------------|-----------|
| 2026-11-18 | Agente — codex/fase1-conformidade-editorial | Criação do padrão inicial |
| 2026-11-18 | Agente 3 — codex/etapa3-agente3-publish-utm | Geração automatizada de URLs via tools/publish_pack.py e tabela de URLs por canal/tenant |
