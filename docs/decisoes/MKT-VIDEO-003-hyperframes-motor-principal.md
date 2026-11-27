# MKT-VIDEO-003 — HyperFrames como motor audiovisual principal

- Status: decisão arquitetural vigente
- Data: 27/11/2026
- Autoridade: pedido explícito do titular (Operação Master HF-001)
- Implementação: `renderers/hyperframes/` (runtime 0.9.103); adaptador e integração em andamento na branch `codex/hyperframes-core-migration`
- Relação com decisões anteriores: **supera, sem revogar o registro histórico**, as afirmações "HyperFrames não foi adotado" de [MKT-VIDEO-001](MKT-VIDEO-001-producao-modular.md) e "nenhuma ferramenta foi adotada por esta decisão" de [MKT-PIPELINE-001](MKT-PIPELINE-001-pipeline-criativo-modular.md); preserva integralmente [MKT-VIDEO-002](MKT-VIDEO-002-video-clean-narracao-separada.md) (VIDEO CLEAN), [MKT-BRAND-001](MKT-BRAND-001-marca-salao-meu-salao-studio-bella.md) e [MKT-PLATFORM-001](MKT-PLATFORM-001-plataforma-multiprojeto.md)

## Contexto

A fábrica atual produz vídeo por composição Python + FFmpeg (`tools/render_local.py`,
`tools/render_pipeline.py`), com contratos neutros em `platform/` e o princípio de que o
renderizador fica atrás de adaptador. Os templates HyperFrames versionados
(`templates/`, pinados em `0.8.126`) e o `tools/edit_link_reel.py` (que já invoca
`npx hyperframes render`) comprovaram a viabilidade do motor. O titular decidiu
(27/11/2026) promover o HyperFrames a motor principal de composição e renderização,
encerrando o desenvolvimento paralelo de recursos próprios de animação/tipografia/timeline.

## Decisão

1. **HyperFrames é o motor principal de composição e renderização audiovisual** para
   novas produções do projeto: composições HTML determinísticas (`data-*` + GSAP seekable),
   validação (`check`), preview (Studio) e render (CLI/Producer).
2. **A fábrica existente é preservada** como orquestração e inteligência editorial:
   contratos (`platform/`), Video Studio, fila, biblioteca de mídia, revisão/aprovação,
   guardrails multi-tenant, empacotamento ZIP e histórico. Não é descartada.
3. **FFmpeg permanece como infraestrutura técnica**: codificação, processamento,
   normalização, conferência (ffprobe) e fallback do renderizador legado
   (`render_local`/`render_pipeline`), que continua reproduzindo entregas anteriores.
4. **Não será construído um segundo motor concorrente.** Recursos próprios de animação,
   tipografia e timeline não serão estendidos, salvo necessidade comprovada e registrada.
5. **A integração fica atrás de adaptador**, exatamente como previsto em MKT-VIDEO-001:
   o valor `renderer.adapter: "hyperframes"` no contrato `Composition`; campanhas não
   dependem de argumentos internos da CLI. O adaptador traduz contratos neutros
   (VideoRequest/CarouselRequest/OutputPlan/AssetManifest) em projeto HyperFrames e
   devolve os mesmos artefatos de entrega (MP4 sem áudio, narração TXT, manifesto,
   ZIP).
6. **VIDEO CLEAN (MKT-VIDEO-002) aplica-se integralmente ao novo motor**: composições
   mudas, sem `<audio>`, sem legendas narrativas queimadas, sem SRT por padrão, exportação
   sem faixa de áudio, narração TXT separada. O modo legado com legendas/SRT permanece
   para campanhas antigas, sem transformação retroativa.
7. **Seleção de renderizador é explícita e registrada**: `hyperframes` (padrão para novas
   composições validadas), `local-proof-render`/`local-pipeline-render` (legado/fallback),
   e o manifesto de entrega registra qual motor produziu a peça. Fallback nunca é
   silencioso.
8. **Templates históricos (`templates/`) permanecem intocados** (classificados como
   terceiros/gerados). Novos templates nativos vivem em
   `renderers/hyperframes/compositions/` e derivam de guardrails e brand-kit, nunca de
   claims antigos.
9. **Versões são fixadas**: `hyperframes@0.9.103` + `@hyperframes/producer@0.9.103`
   (exatas, com lockfile). Atualização segue política controlada
   (`docs/migracao-hyperframes/ATUALIZACOES-E-ROLLBACK.md`).
10. **Sem publicação automática**: `autoPublish: false`, aprovação humana e as demais
    regras comerciais de `AGENTS.md` permanecem. `hyperframes publish`, cloud rendering e
    login HeyGen exigem autorização específica do titular.

## O que esta decisão não autoriza

- Merge na main, deploy, publicação nas redes ou compartilhamento público.
- Exclusão ou reescrita de módulos legados, entregas anteriores ou documentos históricos.
- Uso de serviços pagos, cloud rendering ou telemetria obrigatória (telemetria desativada).
- Mistura de identidades de tenants ou alteração das decisões de marca.

## Registro de contradição resolvida

- `docs/decisoes/MKT-VIDEO-001` (linhas "HyperFrames não foi adotado") e
  `docs/decisoes/MKT-PIPELINE-001` ("nenhuma ferramenta foi adotada por esta decisão")
  permanecem **como registro histórico de intenção** de 22/11/2026, com nota de
  classificação datada apontando para esta decisão. O histórico não é reescrito.
- `WORKFLOW.md` já listava HyperFrames como ferramenta do fluxo antes desta decisão;
  a partir dela, essa menção deixa de ser divergência e passa a refletir a arquitetura.
- `platform/README.md` ("Nenhum renderizador foi implementado... HyperFrames não foi
  instalado") descrevia o estado até 27/11/2026; a instalação e o adaptador passam a
  existir em `renderers/hyperframes/`.

## Referências

- Operação Master HF-001 (instrução do titular, 27/11/2026).
- Documentação da migração: [../migracao-hyperframes/](../migracao-hyperframes/README.md).
- Runtime instalado: [../../renderers/hyperframes/README.md](../../renderers/hyperframes/README.md).
