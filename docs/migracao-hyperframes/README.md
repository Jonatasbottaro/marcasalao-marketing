# Migração HyperFrames (HF-001)

Documentação da migração arquitetural que promove o **HyperFrames** a motor principal de
composição e renderização audiovisual do projeto, preservando a fábrica existente como
orquestração, inteligência editorial e governança.

- Decisão canônica: [MKT-VIDEO-003 — HyperFrames como motor audiovisual principal](../decisoes/MKT-VIDEO-003-hyperframes-motor-principal.md)
- Runtime instalado: [renderers/hyperframes/](../../renderers/hyperframes/README.md)
- Branch técnica: `codex/hyperframes-core-migration` (base: `main` + commits da
  `codex/operacao-resultado-26`, que incluem `frame.md` e o fix VIDEO CLEAN do Studio)

## Índice

| Documento | Conteúdo |
| --- | --- |
| [INVENTARIO-DOCUMENTAL.md](INVENTARIO-DOCUMENTAL.md) | Classificação dos documentos existentes relevantes à migração |
| [INVENTARIO-FUNCIONAL.md](INVENTARIO-FUNCIONAL.md) | Funcionalidades em código × documentação; lacunas |
| [MATRIZ-DE-MIGRACAO.md](MATRIZ-DE-MIGRACAO.md) | Recurso → destino (MANTER/ADAPTAR/MIGRAR/FALLBACK/LEGADO) |
| [ARQUITETURA-ALVO.md](ARQUITETURA-ALVO.md) | Arquitetura HyperFrames-first e fluxo ponta a ponta |
| [CONTRATOS-E-ADAPTADORES.md](CONTRATOS-E-ADAPTADORES.md) | Mapeamento de contratos → composição HyperFrames |
| [DECISOES-E-CONFLITOS.md](DECISOES-E-CONFLITOS.md) | Contradições históricas e sua resolução |
| [PLANO-DE-EXECUCAO.md](PLANO-DE-EXECUCAO.md) | Fases, estado e próximos passos |
| [CRITERIOS-DE-ACEITE.md](CRITERIOS-DE-ACEITE.md) | Critérios de conclusão verificáveis |
| [RUNBOOK-OPERACIONAL.md](RUNBOOK-OPERACIONAL.md) | Operação diária do novo motor |
| [ATUALIZACOES-E-ROLLBACK.md](ATUALIZACOES-E-ROLLBACK.md) | Política de atualização e reversão |
| [EVIDENCIAS.md](EVIDENCIAS.md) | Registro de evidências por fase |

## Estado em uma linha

Instalação concluída e validada (0.9.103, smoke test verde, caches confinados);
documentação e matriz publicadas; adaptador, integração com Studio/fila, templates
nativos e campanha piloto em execução — ver [PLANO-DE-EXECUCAO.md](PLANO-DE-EXECUCAO.md).

## Regras que governam esta migração

- `AGENTS.md` na íntegra: portabilidade (`<RAIZ>`), worktrees, `.workspace/`, handoff.
- VIDEO CLEAN ([MKT-VIDEO-002](../decisoes/MKT-VIDEO-002-video-clean-narracao-separada.md)):
  sem áudio, sem legendas queimadas, sem SRT por padrão, narração TXT separada.
- Guardrails multi-tenant e `autoPublish: false`; sem publicação/merge/deploy.
- Templates históricos (`templates/`) são terceiros/gerados: não editar.
- Nada é declarado concluído sem evidência executável ([EVIDENCIAS.md](EVIDENCIAS.md)).
