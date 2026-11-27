# Documentação do Marca Salão Marketing — ponto de entrada central

Este é o **ponto de entrada único** da documentação versionada do projeto, para qualquer
IDE ou agente. Ele não substitui as fontes canônicas: aponta para elas. Regras operacionais
continuam em [AGENTS.md](../AGENTS.md); este índice organiza o resto.

- **Base verificada deste índice:** branch `main`, commit
  `05ca7fa10209c648c5ea9cfb5d8a358214c8c396` (2026-11-22). Consolidação documental registrada
  em [auditorias/CONSOLIDACAO-DOCUMENTAL-2026-11-22.md](auditorias/CONSOLIDACAO-DOCUMENTAL-2026-11-22.md).
- **Adendo HF-001 (27/11/2026, branch `codex/hyperframes-core-migration`):** migração do
  motor audiovisual para HyperFrames — ver [migracao-hyperframes/](migracao-hyperframes/README.md)
  e [decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md](decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md).
- **Estado técnico consolidado:** [contexto/ESTADO-ATUAL.md](contexto/ESTADO-ATUAL.md).
- **Inventário e situação de cada documento:** [governanca/MAPA-DOCUMENTAL.md](governanca/MAPA-DOCUMENTAL.md).
- **Regras de manutenção documental:** [governanca/DOCUMENTACAO.md](governanca/DOCUMENTACAO.md).
- **CI, gates locais e padrão de Pull Requests:** [governanca/CI-E-PRS.md](governanca/CI-E-PRS.md)
  (template em [.github/PULL_REQUEST_TEMPLATE.md](../.github/PULL_REQUEST_TEMPLATE.md)).

> Números, contagens e comandos abaixo foram reconferidos por leitura de código na base
> indicada. Resultados de testes citados em outros documentos são **históricos**, com data
> e SHA próprios; nada nesta consolidação foi executado.

## 1. Ordem de leitura para retomar o trabalho

1. [AGENTS.md](../AGENTS.md) — contrato operacional: armazenamento em `<RAIZ>`, portabilidade
   entre estações, autorizações de publicação/arte/áudio, memória e handoff obrigatório.
2. [contexto/README.md](contexto/README.md) — procedimento de retomada e fontes por assunto.
3. [contexto/ESTADO-ATUAL.md](contexto/ESTADO-ATUAL.md) — o que está implementado e integrado,
   o que está só em branch, o que é proposta, pendências e evidências.
4. [contexto/PROXIMOS-PASSOS.md](contexto/PROXIMOS-PASSOS.md) — backlog priorizado, critérios
   de aceite e itens que exigem autorização do titular.
5. [contexto/HANDOFF.md](contexto/HANDOFF.md) — resumo da última tarefa relevante e próxima
   ação segura.
6. O guia canônico do assunto da tarefa (seção 3 abaixo).
7. [WORKFLOW.md](../WORKFLOW.md) — fluxo editorial de marketing e regra de vídeo sem áudio.

Antes de implementar qualquer coisa: confira branch, HEAD completo, `git status`, worktrees e
sessões concorrentes; `origin/main` local pode estar desatualizado (fetch/pull exigem
autorização específica). Não trate documento histórico como autorização.

## 2. As quatro frentes do projeto (não misturar)

| Frente | O que é | Fonte canônica |
| --- | --- | --- |
| **Fábrica multi-tenant** | Contratos JSON → render FFmpeg → pacotes → calendário → portal → gates. Publicação sempre manual. | [arquitetura-fabrica.md](arquitetura-fabrica.md) |
| **Video Studio local** | Painel HTTP em `127.0.0.1` para criar/revisar/exportar Vídeo, Carrossel e Motion; biblioteca de mídia; fila; ZIP de entrega. | [../tools/produce/README.md](../tools/produce/README.md) |
| **Editorial de campanhas** | Briefing → hooks → roteiro → legendas → aprovação → publicação manual → mensuração. | [../00-briefings/README.md](../00-briefings/README.md) e documentos da própria campanha |
| **Integrações de marca** | ComfyUI/Postiz/Hermes por marca, com guard de proveniência; escopo e estação próprios. | [../marcas/marcasalao/comfyui/README.md](../marcas/marcasalao/comfyui/README.md), [hermes/README.md](hermes/README.md) |

O núcleo TypeScript (`platform/`) e a orquestração (`orchestration/temporal/`) são
**camadas técnicas internas**: contratos puros e piloto local, sem publicação e sem deploy.
Fontes: [../platform/README.md](../platform/README.md) e
[../orchestration/temporal/README.md](../orchestration/temporal/README.md).

## 3. Fontes canônicas por assunto

| Assunto | Fonte canônica | Observação |
| --- | --- | --- |
| Regras de operação e autorização | [AGENTS.md](../AGENTS.md) | Prevalece sobre qualquer guia; IDEs carregam automaticamente |
| Fluxo de marketing e vídeo sem áudio | [WORKFLOW.md](../WORKFLOW.md) | Regra essencial; detalhes de produção nos guias abaixo |
| Estado técnico / integração / pendências | [contexto/ESTADO-ATUAL.md](contexto/ESTADO-ATUAL.md) | Único lugar para "o que está na main" |
| Backlog e critérios de aceite | [contexto/PROXIMOS-PASSOS.md](contexto/PROXIMOS-PASSOS.md) | Propostas nunca como implementação |
| CI, gates locais e padrão de PRs | [governanca/CI-E-PRS.md](governanca/CI-E-PRS.md) | 5 workflows reais + checklist de PR |
| Retomada entre sessões/estações | [contexto/HANDOFF.md](contexto/HANDOFF.md) | Handoff ≠ autorização |
| Arquitetura da fábrica, gates, lentes, manifests | [arquitetura-fabrica.md](arquitetura-fabrica.md) | Contagens reconferidas na base deste índice |
| Rotina diária/semanal do titular | [guia-operacional-titular.md](guia-operacional-titular.md) | Aprovação, handoff, publicação manual, reparo |
| Operação do Studio (CLI + painel + ZIP) | [../tools/produce/README.md](../tools/produce/README.md) | Inclui multiformato, cortes, Motion, biblioteca |
| Render local / adaptador / determinismo | [../tools/render/README.md](../tools/render/README.md) | Limites de determinismo documentados lá |
| Portal de revisão | [../05-review-portal/README.md](../05-review-portal/README.md) | **Gerado** por `tools/review_dashboard.py`; não editar à mão |
| Calendário editorial e matriz UTM | [../04-legendas/calendario-editorial.md](../04-legendas/calendario-editorial.md) | **Gerado** por `tools/campaign_calendar.py`; não editar à mão |
| Analytics, UTM e rotina semanal | [analytics-utm-playbook.md](analytics-utm-playbook.md), [rastreio-utm.md](rastreio-utm.md) | Métricas do repositório são sintéticas até importação real |
| Mensuração e destinos NS-001/NS-002 | [../05-mensuracao/GUIA-MENSURACAO-NS001-NS002.md](../05-mensuracao/GUIA-MENSURACAO-NS001-NS002.md), [../06-validacao-destinos/GUIA-VALIDACAO-DESTINOS-NS001-NS002.md](../06-validacao-destinos/GUIA-VALIDACAO-DESTINOS-NS001-NS002.md) | Ensaios com dados fictícios |
| Novo tenant/nicho | [guia-novo-nicho.md](guia-novo-nicho.md) | Onboarding manual; scaffolder existe com ressalvas (ver ESTADO-ATUAL) |
| Decisões de arquitetura | [decisoes/](decisoes/) | **Registros históricos de intenção**; estado real no ESTADO-ATUAL |
| Identidades de marca (vigente) | [decisoes/MKT-BRAND-001-marca-salao-meu-salao-studio-bella.md](decisoes/MKT-BRAND-001-marca-salao-meu-salao-studio-bella.md) | Marca Salão comercial / Meu Salão experiência+PWA / Studio Bella demonstração; não renomear o PWA |
| Motor audiovisual principal (vigente) | [decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md](decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md) | HyperFrames como motor principal; fábrica preservada como orquestração; FFmpeg fallback; sem fallback silencioso |
| Migração HyperFrames (HF-001) | [migracao-hyperframes/README.md](migracao-hyperframes/README.md) | Inventários, matriz, arquitetura-alvo, contratos, runbook, rollback e evidências da migração |
| Planejamento R001/TEMPORAL | [planejamento/](planejamento/) | Especificações; partes implementadas, partes em revisão |
| Especificações aprovadas (EGM) | [designs/SITEMAP.md](designs/SITEMAP.md) | Bundle EGM em `.agents/plugins/egm/` (terceiros) |
| Integrações Hermes/Postiz/ComfyUI | [hermes/README.md](hermes/README.md), [../marcas/marcasalao/comfyui/FLUXO-COMPLETO-MARCA-SALAO.md](../marcas/marcasalao/comfyui/FLUXO-COMPLETO-MARCA-SALAO.md) | Escopo por marca e por estação; guards fail-closed |
| Auditorias e consolidações | [auditorias/](auditorias/) | Referência de problemas, não prova automática do estado |
| Aceites e sessões passadas | [historico/](historico/), [../contexto_projeto.md](../contexto_projeto.md), [../.workspace/devlogs/](../.workspace/devlogs/) | **Histórico**: não alterar resultados retroativamente |
| Contratos por tenant | [../tenants/](../tenants/) + [../schemas/](../schemas/) | Contratos, não documentação genérica |
| Templates de produção | [../templates/CAMPAIGN_TEMPLATE.md](../templates/CAMPAIGN_TEMPLATE.md) | Estrutura de entrega; regras em AGENTS/WORKFLOW |

## 4. O que este índice deliberadamente não faz

- Não copia regras de [AGENTS.md](../AGENTS.md) nem de [WORKFLOW.md](../WORKFLOW.md):
  resume e aponta, para não criar versões independentes das regras.
- Não transforma briefings, hooks, roteiros, legendas e posts em documentação de
  arquitetura: conteúdo editorial permanece nas pastas de campanha.
- Não reorganiza bundles de terceiros em `.agents/` nem edita arquivos gerados
  (`05-review-portal/`, `04-legendas/calendario-editorial.*`, `matriz-utm-consolidada.csv`,
  `02-reels-shorts/deliveries/factory-report.json`) sem identificar o gerador.
- Não promete sincronização automática entre estações: o alinhamento é por Git;
  `.workspace/`, aprovações e mídia local **não** sincronizam.
- Não autoriza implementar backlog, produzir mídia, publicar ou agendar nada.

## 5. Manutenção

Qualquer tarefa que mude contrato, comportamento, contagens ou comandos deve atualizar a
fonte canônica correspondente **na mesma entrega**, conforme
[governanca/DOCUMENTACAO.md](governanca/DOCUMENTACAO.md). Divergência entre documento e
código resolve-se corrigindo o documento para refletir o código verificado — ou registrando
o defeito do código no backlog — nunca reescrevendo a regra para legitimar o defeito.