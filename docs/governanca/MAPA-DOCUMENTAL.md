# Mapa documental consolidado

Inventário da documentação versionada na base `main` @
`05ca7fa10209c648c5ea9cfb5d8a358214c8c396` (2026-11-22), com categoria, situação, fonte
canônica relacionada e ação desta consolidação. Política de manutenção:
[DOCUMENTACAO.md](DOCUMENTACAO.md). Entrada central: [../README.md](../README.md).

**Decisão de organização desta consolidação: nenhum arquivo foi movido.** Motivos:
(i) consumidores de código dependem de caminhos atuais (seção 4); (ii) links relativos
internos e âncoras permaneceriam válidos sem risco; (iii) a tarefa proíbe perda de conteúdo
e apagamento. A centralização é feita por **índice + fontes canônicas + banners de
classificação**, não por movimentação física. Caminhos antigos → novos: **nenhum**.

Categorias: `propria` (documentação do projeto) · `gerado` (produzido por ferramenta) ·
`editorial` (conteúdo de campanha) · `historico` (registro de sessão/aceite/decisão) ·
`terceiros` (bundle externo) · `local` (não versionado, por estação).
Situação: `vigente` · `historico` · `proposta` · `duplicado` · `conflitante`.

## 1. Entrada e regras (raiz)

| Caminho | Finalidade | Categoria | Situação | Canônico related | Ação |
| --- | --- | --- | --- | --- | --- |
| `README.md` | Apresentação e entrada | propria | vigente (contagens corrigidas nesta consolidação) | `docs/README.md` | atualizado: resumo + links; tabela de campanhas corrigida; matriz de formatos mantida com nota de data |
| `AGENTS.md` | Contrato operacional dos agentes | propria | vigente | — | atualizado (rodada de alinhamento): caminhos de servidor substituídos por referências portáteis versionadas + nota de runtime; referências a `docs/README.md` e governança na continuidade técnica |
| `CLAUDE.md` | Entrada de IDE alternativa | propria | vigente (espelho enxuto) | `AGENTS.md` | atualizado: encaminha às mesmas fontes; diretiva `EGM artifact directory: .workspace/tmp/egm` preservada |
| `WORKFLOW.md` | Fluxo de marketing + vídeo sem áudio | propria | vigente | `docs/README.md` §3 | atualizado: fluxo atual ponta a ponta em 6 passos + caminho manual legado rebaixado; links canônicos |
| `contexto_projeto.md` | Devlog acumulativo de sessões | historico | histórico (topo desatualizado) | `docs/contexto/ESTADO-ATUAL.md` | banner de classificação; conteúdo preservado |
| `contexto_projeto_6.md` | Consolidação v6 pós-Etapa 13.1 | historico | histórico (snapshot de `642f570`) | `docs/contexto/ESTADO-ATUAL.md` | banner de snapshot com base/data; números preservados como medição daquela base |

## 2. Contexto e governança (`docs/contexto/`, `docs/governanca/`)

| Caminho | Finalidade | Categoria | Situação | Ação |
| --- | --- | --- | --- | --- |
| `docs/contexto/README.md` | Procedimento de retomada e fontes | propria | vigente | atualizado: ordem de leitura inclui entrada central e governança |
| `docs/contexto/ESTADO-ATUAL.md` | Estado técnico consolidado | propria | vigente + seções históricas | atualizado: seção nova "Base verificada em 22/11/2026" no topo; marcos antigos preservados |
| `docs/contexto/PROXIMOS-PASSOS.md` | Backlog e critérios | propria | vigente + propostas | atualizado: backlog consolidado da auditoria no topo, marcado como proposta |
| `docs/contexto/HANDOFF.md` | Retomada entre sessões | propria | vigente | atualizado: resumo da consolidação e da auditoria |
| `docs/governanca/DOCUMENTACAO.md` | Política de manutenção | propria | **novo** | criado |
| `docs/governanca/MAPA-DOCUMENTAL.md` | Este inventário | propria | **novo** | criado |
| `docs/governanca/CI-E-PRS.md` | Mapa de CI, gates locais e padrão de PRs | propria | **novo** (rodada de alinhamento de 22/11/2026) | criado |
| `docs/README.md` | Entrada central | propria | **novo** | criado |

## 3. Guias operacionais e arquitetura (`docs/`)

| Caminho | Finalidade | Categoria | Situação | Canônico related | Ação |
| --- | --- | --- | --- | --- | --- |
| `docs/arquitetura-fabrica.md` | Arquitetura da fábrica, gates, lentes, manifests | propria | vigente com trechos obsoletos | código (`tools/`) | atualizado: 8 domínios, 7 lentes, 51 módulos/4 faixas, comandos reais; trechos Etapa 5B marcados como históricos |
| `docs/guia-operacional-titular.md` | Rotina diária/semanal do titular | propria | vigente com contagens obsoletas | `docs/arquitetura-fabrica.md` | atualizado: contagens e flags reais |
| `docs/guia-novo-nicho.md` | Onboarding manual de tenant | propria | vigente (scaffolder existe com ressalvas) | `tools/tenant_scaffolder.py` | atualizado: nota sobre scaffolder + bloco de exclude portável como proposta |
| `docs/analytics-utm-playbook.md` | Rotina de analytics/UTM | propria | vigente | `tools/utm_report_importer.py` | mantido; métricas sintéticas já declaradas |
| `docs/rastreio-utm.md` | Convenções de parâmetros UTM | propria | vigente | `tools/campaign_calendar.py` | mantido (referenciado por código) |
| `docs/checklist-decisoes-titular.md` | Decisões abertas pré-publicação | propria | vigente (3 decisões abertas em 21/11) | titular | mantido |
| `docs/ARQUIVAMENTO-DE-CAMPANHAS.md` | Como arquivar material aprovado | propria | vigente | — | mantido |
| `docs/decisoes/MKT-VIDEO-001-*.md` | Decisão de produção modular | historico | histórico ("não iniciada" superado) | `platform/README.md` | banner de registro histórico |
| `docs/decisoes/MKT-PLATFORM-001-*.md` | Decisão de núcleo multiprojeto | historico | histórico (idem) | `platform/README.md` | banner |
| `docs/decisoes/MKT-PIPELINE-001-*.md` | Decisão de pipeline por beats/assets | historico | histórico (parcialmente implementado) | `docs/contexto/ESTADO-ATUAL.md` | banner |
| `docs/planejamento/R001-formatos-sociais.md` | Catálogo de formatos e regras oficiais | propria | vigente (fontes certificadas em 07/11) | `platform/src/output-profiles/rules.ts` | mantido |
| `docs/planejamento/R001-changelog.md` | Changelog da revisão R001 | historico | histórico | — | mantido |
| `docs/planejamento/TEMPORAL-01-*.md` | Especificação do piloto | historico | histórico (implementado) | `orchestration/temporal/README.md` | banner |
| `docs/planejamento/TEMPORAL-02-*.md` | PRD de validação no Temporal | proposta | proposta em revisão (fatias integradas) | `docs/contexto/ESTADO-ATUAL.md` | banner de estado parcial |
| `docs/designs/README.md`, `SITEMAP.md`, `GUIA-EGM.md`, `RODADA-NOTURNA-*.md` | Especificações aprovadas via EGM | propria | vigente | `.agents/plugins/egm/` | mantidos |
| `docs/hermes/README.md` + 12 documentos datados | Prompts e configuração Hermes/Postiz | historico | histórico (out–nov/2026), regras vigentes em AGENTS | `marcas/*/comfyui/` | mantidos como histórico |
| `docs/historico/README.md` + 13 aceites | Registros de sessão e aceite | historico | histórico | — | mantidos |
| `docs/auditorias/AUDITORIA-PROJETO-2026-11-22.md` | Auditoria somente leitura | propria | vigente (referência de problemas) | código na base `01074c8` | trazido para esta base; não é prova automática |
| `docs/auditorias/CONSOLIDACAO-DOCUMENTAL-2026-11-22.md` | Relatório desta consolidação | propria | **novo** | — | criado |

## 4. Dependências de caminho em código (não mover)

| Documento | Consumidor | Efeito |
| --- | --- | --- |
| `contexto_projeto.md` | `tools/devlog_sync.py:270,337` (alvo padrão) | mover quebraria a consolidação de devlogs |
| `05-review-portal/README.md` | `tools/review_dashboard.py:690,709`; `tools/release_audit.py:76`; `tools/factory_cli.py:53` | arquivo **gerado**; faz parte do gate |
| `docs/rastreio-utm.md` | `tools/campaign_calendar.py:443,1211,1231` (texto de saída) | referência textual em mensagens |
| `docs/analytics-utm-playbook.md` | `tools/utm_report_importer.py:1449`; `tools/utm_simulator.py:521` | idem |
| `docs/planejamento/TEMPORAL-01-*.md` | `.github/workflows/temporal-pilot-ci.yml:12,17` (filtro de path) | mover alteraria gatilho de CI |
| `AGENTS.md`, `CLAUDE.md`, `docs/designs/{README,SITEMAP,GUIA-EGM}.md` | `tools/verify_egm_install.py:206,217` | verificação offline do EGM |
| `templates/*/AGENTS.md`, `templates/*/CLAUDE.md` | carregados por IDEs nos templates | encaminham para raiz; mantidos |

## 5. Documentação técnica de módulos (READMEs de pasta)

| Caminho | Categoria | Situação | Ação |
| --- | --- | --- | --- |
| `platform/README.md` (1212 l.) | propria | vigente | mantido; fonte do núcleo TS |
| `orchestration/temporal/README.md` + `docs/TEMPORAL-02-ELEPHANT-GOLDFISH.md` | propria/historico | vigente + registro de gate | mantidos |
| `tools/produce/README.md` (646 l.) + `studio-preflight.md`, `studio-delivery-verification.md`, `studio-work-backup.md` | propria | vigente | mantidos; canônico do Studio |
| `tools/render/README.md` | propria | vigente | mantido; canônico do render local |
| `tenants/*/campaigns/README.md` (5) | propria | **conflitante** (listam subconjunto das campanhas) | registrados como pendência de índice; não editados nesta consolidação (índices de contrato exigem tarefa própria) |
| `marcas/marcasalao/comfyui/{README,HERMES-POSTIZ,FLUXO-COMPLETO-MARCA-SALAO}.md` | propria | vigente (runbooks do Servidor02) | banners de escopo de estação adicionados na rodada de alinhamento (caminhos absolutos são runtime do servidor; equivalentes portáteis versionados nesta pasta) |
| `marcas/multitrackhub/comfyui/{README,HERMES-POSTIZ-MULTITRACKHUB,POSTIZ-LIMPEZA-POS-PUBLICACAO}.md` | propria/historico | vigente + histórico de limpeza | banner de escopo de estação em `HERMES-POSTIZ-MULTITRACKHUB.md`; demais mantidos |
| `marcas/multitrackhub/identidade-visual/README.md` | propria | vigente | mantido |
| `05-review-portal/README.md` | **gerado** | vigente | não editar à mão |
| `01-insta-stories/{README,EDITAR_CAPCUT}.md`, `02-hooks/README.md`, `03-roteiros/README.md`, `03-youtube-pdf/README.md`, `04-legendas/README.md`, `02-reels-shorts/README.md`, `videos_brutos/README.md` | propria | vigente (guias de pasta) | `01-insta-stories/README.md` e `02-reels-shorts/README.md` corrigidos na rodada de alinhamento (instrução de "adicionar áudio" removida; caminho absoluto de AppImage removido); demais mantidos |
| `templates/CAMPAIGN_TEMPLATE.md` | propria | vigente | mantido |
| `.github/RELEASE_TEMPLATE.md` | propria | **corrigido** na rodada de alinhamento (instrução de adicionar áudio e item "Áudio gravado" removidos; checklist de entrega muda) | mantido no caminho (template do GitHub) |
| `.github/PULL_REQUEST_TEMPLATE.md` | propria | **novo** na rodada de alinhamento | criado |
| `docs/historico/README.md` | propria | vigente | índice ampliado para os 15 registros da pasta |
| `memory/common/_rules/referencias-publicadas-recentes.md` | propria | vigente (regra de referências) | mantido |

## 6. Conteúdo editorial e evidências (não reorganizar)

| Conjunto | Qtd. | Categoria | Situação | Ação |
| --- | --- | --- | --- | --- |
| `00-briefings/` (README, TEMPLATE, NS-001, NS-002 + validações) | 7 md | editorial | vigente (NS-001/NS-002 em validação) | mantidos no caminho |
| `02-hooks/campanhas/*`, `03-roteiros/campanhas/*` | 5 md | editorial | rascunho/validação | mantidos |
| `04-legendas/pacotes-publicacao/<tenant>/<slug>/*.md` | 42 md | **gerado** por `publish_pack` | vigente | não editar à mão |
| `04-legendas/{calendario-editorial.md,instagram_captions,legendas_cards,roteiro_*}` | 6 md | gerado/editorial | vigente/histórico | mantidos |
| `02-reels-shorts/{demo_link_agendamento,ns-001-*,ns002-piloto-01,r002-agenda-ficticia}/*.md` | 7 md | editorial/historico | provas técnicas, não campanhas aprovadas | mantidos |
| `marcas/marcasalao/posts/*/README.md` | 17 md | editorial | histórico de publicações | mantidos |
| `marcas/multitrackhub/posts/*/README.md` | 11 md | editorial | histórico de publicações | mantidos |
| `05-mensuracao/`, `06-validacao-destinos/` (guias + CSVs) | 2 md | propria | ensaios fictícios declarados | mantidos |
| `.workspace/devlogs/etapa5-*.md`, `etapa6-*.md` | 19 md | historico (versionado de propósito) | histórico | mantidos; consolidação via `devlog_sync` |

## 7. Terceiros e local (fora do escopo de edição)

| Conjunto | Categoria | Ação |
| --- | --- | --- |
| `.agents/skills/*`, `.agents/plugins/egm/*`, `.agents/plugins/marketplace.json` (1199 arquivos) | terceiros | não reorganizar |
| `templates/*/hyperframes.json`, `index.html`, `package.json` | terceiros/gerados | não editar |
| `.workspace/{archives,logs,reports,studio,tmp,tools,bundles,snapshots}` | local por estação | não versionar; não limpar nesta tarefa |
| `platform/dist/`, `tools/studio/frontend/dist/` | gerado, não rastreado | não editar |

## 8. Cobertura deste inventário

- **Lidos integralmente nesta tarefa ou na auditoria da mesma data:** todos os documentos
  das seções 1–3, READMEs técnicos da seção 5 (via levantamentos delegados da auditoria),
  cabeçalhos e estados dos editoriais da seção 6.
- **Apenas inventariados (título/primeiras linhas + contagem):** os 42 pacotes sociais,
  os 28 READMEs de posts, os 19 devlogs, os 12 documentos datados de `docs/hermes/`,
  os 13 aceites de `docs/historico/` e os bundles de `.agents/`.
- **Não verificados:** conteúdo remoto (Postiz/ComfyUI/Hermes), PRs ao vivo, e qualquer
  resultado de execução citado como histórico sem reexecução.