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

## 6. Histórico

| Data       | Autor       | Alteração |
|------------|-------------|-----------|
| 2026-11-18 | Agente — codex/fase1-conformidade-editorial | Criação do padrão inicial |
