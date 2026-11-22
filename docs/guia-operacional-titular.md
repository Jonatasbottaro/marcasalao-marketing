# Guia Operacional do Titular — Fábrica Multi-Tenant

Manual prático para a operação **diária e semanal** da fábrica de conteúdo. Público: o titular (ou a pessoa autorizada por ele). Todos os comandos são executados a partir da raiz do checkout principal (`<RAIZ>`), após alinhar a estação.

> **Regras de ouro (valem sempre)**
>
> 1. **Publicação é manual.** Nenhuma ferramenta deste repositório publica, agenda ou cria rascunho. Todo pacote nasce com `autoPublish: false`.
> 2. **Vídeo sem áudio.** Tenants com política `-an` (`marca-salao`, `meu-salao`, `estudio-flow`, `clinica-vital`) entregam MP4 sem faixa de áudio, com legendas queimadas e sincronizadas. A locução é gerada **fora** do editor, a partir do `<slug>_narracao.txt`. Não insira música, efeitos ou narração no editor de vídeo.
> 3. **Aprovação antes do handoff.** Só entra no pacote diário o que você aprovou expressamente. Decisão `ajuste` nunca entra.
> 4. **Não corrija post publicado.** Ajuste de legenda ou UTM vale para slots futuros; para texto já publicado, edite o post existente e valide. Não presuma que uma edição no Postiz sincroniza o histórico das redes.
> 5. **Portabilidade.** Tudo fica dentro de `<RAIZ>`; auxiliares em `<RAIZ>/.workspace/`. Nunca copie pastas entre máquinas: o alinhamento é por Git.

O ferramental da Etapa 6 está sendo consolidado em paralelo por outros agentes. Os comandos abaixo usam as interfaces previstas; em caso de dúvida sobre uma opção opcional, **`--help` da própria ferramenta é a fonte autoritativa**. A fonte da verdade do comportamento já integrado é [docs/arquitetura-fabrica.md](arquitetura-fabrica.md).

---

## 0. Antes de começar

```bash
git fetch origin --prune && git pull --ff-only
python tools/release_check.py --skip-ts      # gate único: contratos + editorial + doctor + release_audit + empacotamento + E2E
python tools/review_dashboard.py --build --json
```

> **Verificação de release em um comando:** `python tools/release_check.py` orquestra todos os gates oficiais (higiene Git + `autoPublish: false`, TypeScript, 5 tenants, editorial `--strict` de 14 campanhas/7 lentes, `workspace_doctor`, `release_audit --strict` com 8 domínios, `publish_bundler verify` do empacotamento, a suíte Python particionada via `run_tests.py --fast` e a suíte E2E — **9 gates**). Use `--skip-ts` quando o `platform/` já estiver compilado, `--smoke-tests` para o gate de testes rápido, `--full-tests` para incluir os testes de render (as duas são exclusivas entre si) e `--json` para registrar o resultado. Ele nunca publica, agenda ou gera áudio.

O `--build` reconstrói `05-review-portal/index.html`, `portal-data.json` e o `README.md` do portal. O build é determinístico e verifica os hashes SHA-256 de SRT, narração e storyboard contra o `manifest.json` de cada entrega; qualquer divergência aborta com `HASH_DIVERGENTE`. Detalhes em [05-review-portal/README.md](../05-review-portal/README.md).

---

## 1. Revisar campanhas

### 1.1 No portal (recomendado)

```bash
python tools/review_dashboard.py --serve --port 8765
```

Abra `http://127.0.0.1:8765/` no navegador. O servidor é local, somente leitura e vinculado a `127.0.0.1`. Na tela:

1. **Filtre** por tenant, preset, política de áudio e status de aprovação. Use a busca por slug, título, legenda, roteiro ou rota.
2. **Confira o vídeo**: storyboard 2×2, player por variante (quando o MP4 estiver disponível na estação) e a aba **Guardrails & Hashes** — rotas autorizadas, claims bloqueados, `autoPublish: false` e SHA-256. Se o player cair no storyboard com aviso, o MP4 não está nesta estação (isso não é defeito editorial).
3. **Leia as abas de texto**: **Legenda .srt** (blocos com timecodes), **Narração** e as copies **Instagram/YouTube/Facebook** (com a URL UTM destacada e botão Copiar).
4. **Tome a decisão** no controle editorial de cada campanha:
   - **Aguardando Revisão** — ainda não analisada;
   - **Aprovado para Publicação Manual** — libera a campanha para o handoff;
   - **Solicitar Ajuste** — devolve para produção; nunca entra no pacote.
5. Para tenants `-an`, marque a **conferência de locução externa**: você confirmou que o texto de narração será transformado em áudio em ferramenta externa.
6. Registre observações quando houver. As decisões ficam no `localStorage` do navegador e são sincronizadas por `POST /api/approvals` para `.workspace/tmp/aprovacoes-titular.json` (schema v2) quando o portal está servido.

Para conferir ou transportar o que foi decidido:

```bash
python tools/review_dashboard.py --export-aprovacoes
```

Esse comando emite o JSON de aprovações no stdout (redirecione para um arquivo sob `<RAIZ>` se precisar anexá-lo ao handoff). Sem arquivo persistido, encerra com `APROVACOES_AUSENTES`.

### 1.2 Alternativa via terminal

Sem abrir o navegador, use a CLI de aprovações (Etapa 6):

```bash
python tools/approval_cli.py status
python tools/approval_cli.py decide --help
```

`status` mostra o estado atual das decisões por campanha — quantas estão `aguardando`, `aprovado` e `ajuste`, e a conferência de locução externa. `decide` registra a decisão de uma campanha no mesmo arquivo de aprovações usado pelo portal, mantendo o schema v2. Use `--help` para conferir os argumentos exatos (campanha, decisão e observações) antes de registrar.

> O portal e a CLI leem/escrevem o **mesmo** arquivo de aprovações. Registre a decisão em apenas um dos dois canais por vez para não sobrescrever observações.

---

## 2. Gerar o pacote diário de postagem manual

Depois de aprovar no portal ou na CLI:

```bash
python tools/factory_cli.py handoff --all-approved --json
```

Saída (por slot): `.workspace/handoff-diario/<dataSugerida>/<slotId>-<tenantId>-<canal>/` contendo:

| Arquivo | Para que serve |
| --- | --- |
| `POSTAGEM-MANUAL.md` | Ficha de operação: horário BRT, marca, conta, formato, alerta de locução externa, copy, URL UTM completa e checklist de 5 passos |
| `copy-pronta.txt` | Texto UTF-8 limpo, pronto para colar na rede |
| `handoff-manifest.json` | Metadados, hashes SHA-256 esperados, status da mídia local e `autoPublish: false` |
| mídia (quando existir em `.workspace/archives/`) | `<slug>.mp4` (Onda 1), `<slug>-1x1.mp4`/`<slug>-16x9.mp4` (Onda 2) ou `cover.png` |

O comando é **fail-closed**: sem aprovação expressa ele não empacota nada e devolve o motivo `NENHUMA_CAMPANHA_APROVADA_PELO_TITULAR`. Decisões `ajuste` nunca entram. A copy é reauditada contra os guardrails do tenant antes de gravar.

### 2.1 Locução externa (tenants `-an`)

Para `marca-salao`, `meu-salao`, `estudio-flow` e `clinica-vital`:

1. O MP4 entregue **não tem faixa de áudio** — isso é intencional (`-an`, 0 streams no ffprobe).
2. Abra o `<slug>_narracao.txt` da entrega (ou o texto indicado na ficha), organizado por cena e tempo.
3. Gere a locução em ferramenta **externa** ao editor e sincronize com as legendas visíveis do vídeo.
4. Não insira trilha, música ou efeitos no editor. Não confunda faixa silenciosa com narração gerada.

`multitrack-hub` é o único tenant com faixa de áudio permitida (opcional).

### 2.2 Publicação manual nas redes

Use a ficha e a `copy-pronta.txt`; a URL completa já vem com os parâmetros UTM da matriz.

- **Facebook:** cole a URL completa na legenda e indique “Acesse pelo link da descrição”.
- **Instagram:** oriente “Conheça o sistema — link na bio”. Confira antes se o link do perfil está realmente cadastrado. Texto em imagem não é botão e link em legenda não deve ser presumido clicável; adesivo de link em Stories é outro formato e exige autorização específica.
- **Regra de arte compartilhada:** quando a campanha usar a arte quadrada única, mantenha a CTA neutra “Conheça o Marca Salão” na imagem e adapte apenas a legenda por rede.
- Se precisar corrigir texto, **edite o post existente** e valide — não republicue.

### 2.3 Empacotamento determinístico de distribuição (Etapa 11)

O empacotamento consolida artefatos aprovados de uma campanha em pacotes `.zip` portáveis e auditáveis por SHA-256, gravados em `.workspace/bundles/<tenantId>/<slug>/` (não rastreados pelo Git). Cada pacote pertence a um único tenant e nasce com `autoPublish: false`.

```bash
# Empacota somente campanhas aprovadas pelo titular (fail-closed)
python tools/publish_bundler.py pack --tenant <id> --slug <slug> --json

# Empacota prévia sem aprovação expressa (selo PREVIA_NAO_APROVADA)
python tools/publish_bundler.py pack --tenant <id> --slug <slug> --allow-unapproved --json

# Verifica integridade de um bundle existente (SHA-256, entradas, manifesto)
python tools/publish_bundler.py verify --bundle .workspace/bundles/<id>/<slug>/<slug>-v1.zip --json
```

Falha fechada: exige decisão `aprovado` em `.workspace/tmp/aprovacoes-titular.json` a menos que `--allow-unapproved`; decisão `ajuste` nunca entra. Antes de gravar o ZIP, confere o SHA-256 de masters e derivados em `.workspace/archives/` contra o manifesto e o `derivatives.json`. Grava, ao lado do ZIP, um manifesto com `schemaVersion`, `tenantId`, `slug`, `autoPublish: false`, `approvalStatus`, `audioPolicy`, `bundlePath`, `bundleSha256`, `bundleBytes`, `promotionHistory[]`, `items[]` e `bundleSummary`. ZIP bit-determinístico (entradas ordenadas lexicograficamente, data/hora fixa, permissões normalizadas).

---

## 3. Fechar o ciclo semanal (analytics + saúde do checkout)

A rotina semanal está detalhada em [docs/analytics-utm-playbook.md](analytics-utm-playbook.md), seção 7. Resumo operacional:

1. **Exporte métricas** da ferramenta escolhida (GA4, Plausible ou Umami), agrupadas por `utm_source`, `utm_medium`, `utm_campaign` e `utm_content`. A fonte canônica das URLs é `04-legendas/matriz-utm-consolidada.csv` (UTF-8, LF), gerada pelo calendário editorial.
2. **Importe/reconcilie** o relatório com a matriz:

   ```bash
   python tools/utm_report_importer.py --json
   ```

   A ferramenta da Etapa 6 cruza o relatório exportado com a matriz pela chave `(tenant_id, slug, utm_source, utm_medium, utm_content)` e aponta linhas sem correspondência, parâmetros divergentes e colisões de atribuição. Consulte `--help` para informar o arquivo exportado e o diretório de saída.

3. **Analise por tenant, nunca entre nichos diferentes**: `CVR = conversões / sessões`, `share_conversoes` e `delta_onda2` (Onda 2 − Onda 1). Compare canais dentro do mesmo tenant. Sinalize slot com 0 sessões após 72 h, CVR acima de 3× a mediana do tenant e `utm_content` inesperado.
4. **Rode o doctor do workspace**:

   ```bash
   python tools/workspace_doctor.py --check
   ```

   Ele verifica a saúde do checkout (estrutura de diretórios, contratos e artefatos esperados, portabilidade/caminhos e consistência local) e reporta o que precisa de atenção antes do próximo ciclo. Use `--json` para registrar o resultado quando disponível.

5. **Registre decisões no diário da campanha**: data, slot, ferramenta e evidência. Ajuste de UTM vale apenas para slots futuros — nunca edite post publicado para “corrigir” parâmetro.

Checklist de saída: tabela curta por tenant (campanha, canal, formato, sessões, conversões, CVR), top 3 e bottom 3 de `utm_content`, e lista de anomalias com `slot_id` e ação para o próximo ciclo.

### 3.1 Relatório executivo semanal por tenant (Etapa 13)

Depois de importar as métricas, gere o relatório executivo. Ele consolida, **por tenant e sem misturar nichos**, a saúde editorial, a inteligência A/B, a fadiga criativa, os pacotes gerados e a atribuição pós-publicação, e termina com um plano de ação priorizado.

```bash
# todos os tenants da estação
python tools/executive_summary.py --all --json

# um tenant específico, recortado por semana do calendário (1..7)
python tools/executive_summary.py --tenant marca-salao --week 3
```

Saída em `.workspace/reports/<tenantId>/` (local por estação, nunca versionada):

- `relatorio-executivo-<tenantId>.json` — dados estruturados para auditoria;
- `relatorio-executivo-<tenantId>.md` — leitura executiva, com as seções: janela analisada, saúde editorial e aprovações, inteligência A/B e fadiga criativa, entregas e atribuição closed-loop, plano de ação priorizado e fontes.

Como ler:

- **Cabeçalho de governança** — `tenantId`, marca, `generatedAt` em UTC, `weekFilter` e o selo `autoPublish: false`. O relatório é somente leitura: não aprova, não agenda, não publica e não altera datas, canais ou UTMs.
- **Saúde editorial** — total de campanhas do tenant, distribuição `aprovado` / `aguardando` / `ajuste` e o resultado do QA editorial (erros e avisos).
- **Inteligência A/B e fadiga** — taxa de vitória dos testes de hook (`vencedor_A` / `vencedor_B` contra `empate_tecnico`), alertas de `fadiga_detectada` com `zScore` e `pValue`, ranking interno de canais e formatos e as promoções auditadas (`promotionHistory`). Atenção a uma armadilha de unidade: no `tenantBenchmarks`, o campo `abWinRatePct` vem do importer como **fração 0..1**; o relatório mostra a fração e o percentual lado a lado para não haver leitura errada.
- **Entregas e atribuição** — pacotes com SHA-256 verificado, status `reconciliado` contra `aguardando_metricas`, CTR, conversão realizada, `observedUpliftPct` e `winnerSustained`.
- **Plano de ação** — recomendações priorizadas (P1 mais urgente). Nenhuma é executada automaticamente; todas exigem a sua decisão.

Sem relatório UTM ou sem pacotes nesta estação, as seções correspondentes declaram `sem dados` com o motivo — o relatório não inventa métrica nem recalcula estatística. Para habilitá-las, rode antes `utm_report_importer.py --json` e `--reconcile-bundles --json`, ou aponte os artefatos com `--utm-report` e `--bundle-attribution`.

O portal de revisão passa a mostrar o resumo consolidado por tenant (indicadores-chave e caminho/status do relatório). Reconstrua o portal depois de gerar os relatórios:

```bash
python tools/review_dashboard.py --build --json
```

### 3.2 Reparo de mídia local quando o doctor apontar divergência

Se `workspace_doctor --check` reportar `ARCHIVE_HASH_DIVERGENTE`, a mídia local em `.workspace/archives/` divergiu do SHA-256 declarado no manifesto. Isso é local da estação: o vídeo não é versionado, e a cópia de referência fica em `02-reels-shorts/deliveries/<tenant>/<slug>/`.

```bash
# 1. Ver o plano SEM gravar nada (padrão é dry-run)
python tools/workspace_doctor.py --repair --json
python tools/workspace_doctor.py --repair --dry-run --json   # equivalente, explícito

# 2. Aplicar o reparo e revalidar SHA-256 + ffprobe
python tools/workspace_doctor.py --repair --apply --json

# 3. Ou restringir a um tenant / campanha
python tools/workspace_doctor.py --repair --apply --tenant meu-salao --json
python tools/workspace_doctor.py --repair --apply --slug camp-saas-demo-meu-salao-001 --json

# 4. Confirmar que não sobrou erro
python tools/workspace_doctor.py --check --json
```

O que a ferramenta faz, por slot:

- **Master divergente com cópia versionada intacta** → restaura a cópia byte a byte (`restore-from-delivery`). É o caso mais comum e não re-renderiza nada.
- **Master divergente sem cópia intacta** → re-renderiza apenas aquele slot pelo pipeline canônico em diretório temporário isolado e só promove se o SHA-256 produzido for igual ao declarado.
- **Apenas derivados divergentes** (`1:1`, `16:9`, `cover.png`, thumb, grid) → regenera somente os formatos afetados, e apenas se o master do slot estiver íntegro.

Quando não é possível reparar com segurança, a ferramenta **não grava nada** e reporta o motivo em `skippedItems` / `remainingErrors`: `INSUMO_AUSENTE` (sem cópia intacta nem configuração de render), `MASTER_NAO_REPRODUTIVEL` (o render atual não reproduz o hash declarado), `FFPROBE_DIVERGENTE_POS_REPARO` ou `DERIVADO_NAO_REPRODUTIVEL`. Nesses casos o manifesto versionado é a referência e a divergência deve ser tratada como re-release planejado, não como reparo local — decida com o responsável técnico antes de alterar declarações versionadas.

O reparo nunca altera manifesto, calendário, aprovação ou UTM, e nunca publica nem agenda.

---

## 4. Checklist rápido (copiar e colar)

```bash
# 0. Alinhar e validar (gate único)
git fetch origin --prune && git pull --ff-only
python tools/release_check.py --skip-ts       # contratos + editorial + doctor + release_audit + empacotamento + E2E
python tools/tenant_validator.py --all --json

# 1. Revisar (escolha UMA via: portal ou terminal)
python tools/review_dashboard.py --build --json
python tools/review_dashboard.py --serve --port 8765
#   -> http://127.0.0.1:8765/  (aprovar / ajuste + locução externa para -an)
python tools/approval_cli.py status

# 2. Empacotar somente aprovados
python tools/factory_cli.py handoff --all-approved --json
#   -> .workspace/handoff-diario/<data>/<slot>/POSTAGEM-MANUAL.md
#   -> publicar MANUALMENTE; -an => locução gerada fora do editor

# 3. Fechar a semana
python tools/utm_report_importer.py --json
python tools/utm_report_importer.py --reconcile-bundles --json
python tools/workspace_doctor.py --check
#   se houver ARCHIVE_HASH_DIVERGENTE:
python tools/workspace_doctor.py --repair --json          # plano, sem gravar
python tools/workspace_doctor.py --repair --apply --json  # reparo + revalidação
python tools/executive_summary.py --all --json            # relatório por tenant
python tools/review_dashboard.py --build --json           # portal com o digest
python tools/release_audit.py --strict --json
python tools/devlog_sync.py --json

# 4. Suíte de testes particionada (faixas mutuamente exclusivas)
python tools/run_tests.py --smoke --json     # loop de dev / pré-commit (24 módulos)
python tools/run_tests.py --fast --json      # gate oficial de contratos (28 módulos)
python tools/run_tests.py --render --json    # pipeline FFmpeg isolado (22 módulos)
python tools/run_tests.py --all --json       # bateria integral (50 módulos)
python tools/release_check.py --smoke-tests  # checklist rápido com o gate de testes em smoke
```

### 4.1 Qual faixa usar

| Faixa | Quando usar | Módulos | Tempo medido nesta estação |
| --- | --- | --- | --- |
| `--smoke` | a cada iteração de código, antes de commitar | 24 | ~53 s |
| `--fast` | gate oficial de contratos, sem render — é o que o CI roda | 28 | ~6 min |
| `--render` | depois de mexer no pipeline de mídia, com FFmpeg portátil instalado | 22 | depende do hardware |
| `--all` | antes de fechar release | 50 | soma das duas |

`--smoke` é `--fast` menos os 4 módulos de contrato mais caros (`test_release_audit`, `test_studio_mcp`, `test_studio_connections`, `test_editorial_qa`), que montam sandboxes Git, ponte Node/MCP e servidores HTTP. Eles **não** deixam de ser verificados: continuam no `--fast`, que é o gate oficial. Use `--smoke` para iterar rápido e rode `--fast` antes de considerar a entrega pronta.

As quatro flags são mutuamente exclusivas: `--smoke --fast` retorna erro de uso (exit 2). Sem flag, o padrão é `--fast`.

Em todas as faixas os masters de `.workspace/archives/` são fotografados antes do run e restaurados se algum teste os alterar — nenhum teste pode corromper a mídia local.

---

## 5. Referências

- [Arquitetura da fábrica](arquitetura-fabrica.md) — contratos, módulos e gate de release.
- [Portal de revisão](../05-review-portal/README.md) — build, servidor, endpoints e schema de aprovações.
- [Playbook de Analytics & UTM](analytics-utm-playbook.md) — eventos por nicho, GA4/Plausible/Umami e rotina semanal.
- [Padrão de rastreio UTM](rastreio-utm.md) — convenções de parâmetros.
- [Fluxo editorial e regra de vídeo sem áudio](../WORKFLOW.md).
- [Regras do projeto](../AGENTS.md) — portabilidade, `.workspace/` e autorizações.
