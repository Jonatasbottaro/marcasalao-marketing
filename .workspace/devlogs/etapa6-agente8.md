# Devlog — Etapa 6, Agente 8 de 8 (Arquitetura de Documentação e Operações)

- **Data:** 2026-11-20
- **Agente:** Agente 8 de 8 — Arquiteto de Documentação e Operações
- **Branch:** `codex/etapa6-agente8`
- **Worktree:** `<RAIZ>/.workspace/worktrees/etapa6-agente8` (já existia; criada a partir de `main`)
- **<RAIZ> nesta estação:** `C:/Users/Usuario/Documents/GitHub/marcasalao-marketing`
- **Base:** `main` em `8a1b361` (conclusão da Etapa 5B), atualizada com `git fetch origin --prune && git pull --ff-only` no início.

## Escopo executado

| Arquivo | Ação |
| --- | --- |
| `docs/guia-operacional-titular.md` | **Criado.** Manual prático da rotina diária e semanal: (1) revisão no portal `review_dashboard.py --serve` com decisões `aguardando`/`aprovado`/`ajuste`, locução externa conferida para tenants `-an`, exportação de aprovações e alternativa `approval_cli.py status`/`decide`; (2) geração do pacote diário com `factory_cli.py handoff --all-approved`, conteúdo do handoff, lembrete de locução externa e regras de publicação manual por rede (`autoPublish: false`); (3) fechamento semanal com `utm_report_importer.py` + `workspace_doctor.py --check` e rotina do playbook de UTM. Inclui checklist copiável e referências internas. |
| `docs/arquitetura-fabrica.md` | Atualizado para Etapas 2–6: diagrama com a camada da Etapa 6, subcomando `handoff` em 2.6, nova seção 2.18 (tabela com `srt_formatter.py`, `approval_cli.py`, `factory_cli.py handoff`, `utm_report_importer.py`, `workspace_doctor.py`, `uiLabels` no brand-kit e o guia), fluxo operacional com passos 17–20, correção de "4 tenants" para 5, novas referências e nota sobre consolidação das suítes da Etapa 6. |
| `README.md` | Link para o guia no início, comandos 17–20 da Etapa 6 nos comandos rápidos, parágrafo "Operação do titular (Etapa 6)" e checklist ampliado com revisão/aprovação → handoff → publicação manual → importação UTM + doctor. |
| `.workspace/devlogs/etapa6-agente8.md` | Este relatório, para ser transferido ao `contexto_projeto.md` por `devlog_sync.py` na consolidação. `contexto_projeto.md` **não** foi editado diretamente. |

## Verificações exigidas

Script temporário executado de `<RAIZ>/.workspace/tmp/etapa6-agente8/validate_docs.py` sobre os três documentos versionados:

- **Encoding UTF-8:** 3/3 arquivos decodificam estritamente como UTF-8, sem BOM e sem `\ufffd`/mojibake.
- **Links internos:** todos os links relativos dos três arquivos resolvem para arquivos existentes (incluindo os links novos para `guia-operacional-titular.md`, `analytics-utm-playbook.md` e `05-review-portal/README.md`). URLs externas e âncoras foram ignoradas.
- **Caminhos absolutos de usuário:** nenhuma ocorrência de `C:\...`, `/home/`, `/Users/` ou similar. Os únicos `/tmp/` encontrados são parte de `.workspace/tmp/...`, que é caminho relativo portátil; o validador foi ajustado com lookbehind para não gerar falso positivo. Resultado final: **0 problemas**.
- Temporários removidos ao final; nenhum `__pycache__` deixado na worktree.

## Achado importante para a consolidação

No commit-base `8a1b361`, **os módulos da Etapa 6 ainda não existiam na `main` nem nas worktrees irmãs**: não havia `tools/srt_formatter.py`, `tools/approval_cli.py`, `tools/utm_report_importer.py`, `tools/workspace_doctor.py`, nem chave `uiLabels` nos brand-kits/schema, e `factory_cli.py` só registrava os subcomandos `list`, `render` e `pipeline`. Portanto:

- A documentação foi escrita a partir das **interfaces explicitadas no pedido** e das convenções já consolidadas das Etapas 4/5B (portal, aprovações v2, handoff_bundler e playbook UTM).
- Onde uma opção opcional não foi especificada, o guia manda conferir `--help` — não foi inventada nenhuma bandeira como fato verificado.
- As seções 2.18 do Guia e da Arquitetura registram explicitamente esse estado de consolidação. **Ação para o integrador:** ao mergear as branches dos agentes da Etapa 6, reconferir cada assinatura de CLI e atualizar o guia se algum nome/opção divergir.

## Segurança e escopo

- Nenhuma ferramenta de publicação foi executada; nada foi publicado, agendado ou rascunhado.
- Nenhum áudio, TTS ou trilha foi gerado; a regra de vídeo sem áudio e a locução externa foram reforçadas no manual.
- Nenhum contrato, SRT, manifesto ou pacote social foi alterado; nenhum caminho absoluto de estação foi gravado em documento versionado.
- Território respeitado: apenas os quatro arquivos acima.
