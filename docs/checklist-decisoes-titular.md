# Checklist de Decisões do Titular — Pré-Primeira Publicação

> **Versão:** 1.0 · **Data:** 2026-11-21 · **Responsável:** titular
> **Status:** 3 decisões abertas. Enquanto qualquer uma estiver `ABERTA`, a publicação manual fica bloqueada.
> **Escopo:** destravar a operação da fábrica sem alterar `autoPublish: false`, sem publicação automática e sem geração de áudio.

Este documento é o índice objetivo das decisões que só o titular pode tomar. Cada item traz **opções**, **critérios de aceite**, **comandos de verificação** e **o que fica bloqueado**. O detalhe de rastreio está em [rastreio-utm.md](rastreio-utm.md), o de analytics em [analytics-utm-playbook.md](analytics-utm-playbook.md) e a rotina operacional em [guia-operacional-titular.md](guia-operacional-titular.md).

| ID | Decisão | Status | Bloqueia |
| --- | --- | --- | --- |
| **D1** | Identidade visual externa (`Salao02`): atualizar para "Marca Salão" ou manter overlay nas capturas | ABERTA | Arte/copy das capturas e reconferência de evidência |
| **D2** | Ferramenta oficial de analytics (GA4 / Plausible / Umami) e critérios de ativação dos links UTM | ABERTA | Ativação de qualquer URL UTM como "oficial" |
| **D3** | Checklist final: roteiros, fixtures e link da bio `@marcasalao` | ABERTA | Primeira publicação manual |

---

## D1 — Identidade visual externa (`Salao02`)

**Pergunta:** a identidade exibida nas capturas do sistema externo `Salao02` deve ser **atualizada para "Marca Salão"** na origem, ou o projeto deve **manter o overlay** aplicado sobre as capturas existentes?

### Evidência atual no repositório

- `tenants/marca-salao/brand-kit.json` já usa `displayTitle: "MARCA SALAO"`, `headerOverlay.label: "MARCA SALAO"` e `headerOverlay.replaceLegacyLabel: "Meu Salão"`.
- `02-reels-shorts/ns002-piloto-01/README.md` registra que todas as cenas exibem **Marca Salão** no cabeçalho, substituindo qualquer referência legada a "Meu Salão".
- `02-reels-shorts/r002-agenda-ficticia/README.md` registra que o overlay é aplicado por cima da captura (`overlay + fade=alpha=1`), sem modificar a captura original.
- Roteiros NS-001/NS-002 citam reconferência de código no `Salao02` HEAD `91bb5e0`; a NS-001 **não** está autorizada a prometer notificações/lembrete de 24 h.

### Opções

| Opção | Descrição | Pró | Contra |
| --- | --- | --- | --- |
| **A — Atualizar na origem (`Salao02`)** | A interface externa passa a exibir "Marca Salão" nativamente; capturas novas já saem corretas. | Fonte única de verdade; dispensa overlay. | Depende de mudança/branch em outro repositório e de novo commit de evidência; prazo externo. |
| **B — Manter overlay nas capturas (recomendado para destravar)** | O renderer continua sobrescrevendo o cabeçalho via `headerOverlay`, sem tocar no `Salao02`. | Já comprovado no piloto NS-002; determinístico e versionado aqui; não muda a captura original. | Exige conferir cada nova captura para garantir que nada legado apareça fora da área do overlay. |

### Critérios de aceite (qualquer opção)

- [ ] Nenhuma ocorrência visível de "Meu Salão" nas capturas entregues.
- [ ] `headerOverlay.label` e `displayTitle` do brand-kit seguem `"MARCA SALAO"`.
- [ ] Guardrails continuam bloqueando `meu salão` / `meu salao` (`tenants/marca-salao/guardrails.json`).
- [ ] Decisão registrada aqui com data, opção escolhida e referência de commit/evidência.

### Verificação

```bash
python tools/tenant_validator.py --tenant marca-salao --json
python tools/editorial_qa.py --tenant marca-salao --strict --json
python tools/static_cards.py --tenant marca-salao --json
```

---

## D2 — Ferramenta oficial de analytics e ativação dos UTMs

**Pergunta:** qual ferramenta é a oficial — **GA4**, **Plausible** ou **Umami** — e quais critérios autorizam declarar os links UTM da matriz como ativos?

### Estado atual

- `docs/rastreio-utm.md` seção 5 marca **Ferramenta definida: PENDENTE** e exige a marcação `<!-- rastreamento: NÃO CONFIGURADO -->` enquanto não houver validação.
- `docs/analytics-utm-playbook.md` já traz configuração para GA4, Plausible e Umami, catálogo de eventos por nicho e a rotina semanal de importação.

### Critérios de ativação (todos obrigatórios)

1. **Escolha formal:** titular registra a opção (GA4 / Plausible / Umami), o responsável pelo acesso e o link do relatório oficial em `docs/rastreio-utm.md` seção 5.
2. **Domínio e redirect:** URL exata da matriz resolve em HTTPS no `domain` do brand-kit, sem `www`, sem redirect que descarte `utm_*`.
3. **Evento de conversão criado antes da coleta** (ex.: `view_booking_page` para `marca-salao`), marcado como conversão na ferramenta.
4. **Prova de ponta a ponta:** abrir uma URL real em janela anônima e confirmar `utm_source`, `utm_medium`, `utm_campaign` e `utm_content` no relatório em tempo real.
5. **Auditoria local limpa:** `utm_simulator.py --json` com `ok: true`, `collisions: []` e `totalUrls == urlsAudited == urlsOk`.
6. **Só então** remover a marcação `<!-- rastreamento: NÃO CONFIGURADO -->` e declarar os links como ativos. Nunca editar UTM de post já publicado.

### Verificação

```bash
python tools/utm_simulator.py --json
python tools/utm_simulator.py --simulate-traffic --out-dir .workspace/tmp/utm-sim --json
python tools/utm_report_importer.py --json
```

---

## D3 — Checklist final antes da primeira publicação manual

**Pergunta:** roteiros, fixtures e o link da bio do `@marcasalao` estão validados para a primeira publicação?

### Roteiros e fixtures

- [ ] Roteiros NS-001/NS-002 revisados; NS-001 **sem** promessa de reminder/24 h/notificações não validadas.
- [ ] Fixtures editoriais sem placeholders técnicos e com as chaves estruturais exigidas pelo preset `saas-demo`.
- [ ] Guardrails de `marca-salao` aplicados a SRT, narração e legendas sociais (lente `guardrails_cruzados`).
- [ ] SRT com linhas `<= 48` caracteres e duração final igual ao manifesto (30,0 s).

### Link da bio `@marcasalao`

- [ ] O link externo real cadastrado no perfil foi **conferido no perfil** — texto na biografia não basta.
- [ ] A URL aponta para `https://marcasalao.com.br` com os UTMs do slot (quando D2 estiver aprovada).
- [ ] Copy do Instagram usa “Conheça o sistema — link na bio”; Facebook usa a URL completa na legenda com “Acesse pelo link da descrição”.
- [ ] Nenhum botão clicável desenhado na arte; Stories com adesivo de link exigem autorização específica (outro formato).

### Publicação manual

- [ ] Campanha aprovada no portal ou via `approval_cli decide`, com locução externa conferida (tenant `-an`).
- [ ] `factory_cli handoff --all-approved` gerou a ficha e `autoPublish: false` foi conferido no manifesto do pacote.
- [ ] `release_audit --strict` aprovou 7/7 domínios.
- [ ] Nenhum `.mp4`/`.wav` versionado e nenhum áudio gerado no editor.

### Verificação única

```bash
python tools/release_check.py --skip-ts
python tools/tenant_validator.py --all --json
python tools/editorial_qa.py --all --strict --json
python tools/release_audit.py --strict --json
python -m unittest discover -s tests/e2e -v
```

---

## Registro de decisões (preencher no ato)

| ID | Data | Decisão (opção escolhida) | Evidência / referência | Registrado por |
| --- | --- | --- | --- | --- |
| D1 | — | — | — | — |
| D2 | — | — | — | — |
| D3 | — | — | — | — |

> **Lembrete:** aprovar uma decisão aqui não publica nada. A publicação continua manual e exige autorização específica do titular no dia da postagem.
