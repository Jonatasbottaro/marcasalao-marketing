# Inventário documental — migração HyperFrames (HF-001)

Base de verificação: branch `codex/hyperframes-core-migration` @ `89ef85f` (base
`main` `7f1c7ff` + commits da `codex/operacao-resultado-26`), auditada em 27/11/2026.
Categorias conforme [../governanca/DOCUMENTACAO.md](../governanca/DOCUMENTACAO.md)
(`propria`/`gerado`/`editorial`/`historico`/`terceiros`/`local`) e situação
(`vigente`/`historico`/`proposta`/`duplicado`/`conflitante`).

## Entrada e governança

| Caminho | Finalidade | Categoria | Situação | Impacto / ação |
| --- | --- | --- | --- | --- |
| `AGENTS.md` | Regras do projeto (raiz, portabilidade, VIDEO CLEAN, marcas) | própria | vigente | Base normativa da migração; já descreve VIDEO CLEAN na base op26 |
| `WORKFLOW.md` | Fluxo completo de produção | própria | vigente | Já cita HyperFrames como ferramenta; alinhar seção ferramentas ao novo papel |
| `CLAUDE.md` | Espelho enxuto de AGENTS.md + EGM | própria | vigente | Sem alteração necessária |
| `docs/README.md` | Índice central | própria | vigente | **Atualizar**: entrada da migração e da MKT-VIDEO-003 |
| `docs/contexto/ESTADO-ATUAL.md` | Estado técnico (fonte canônica do "que está na main") | própria | vigente (24/11/2026) | **Atualizar**: seção HF-001 no topo quando integrar |
| `docs/contexto/PROXIMOS-PASSOS.md` | Backlog | própria | vigente | **Atualizar**: itens da migração |
| `docs/contexto/HANDOFF.md` | Retomada entre sessões | própria | vigente | **Atualizar**: handoff da HF-001 |
| `docs/governanca/DOCUMENTACAO.md` | Política documental | própria | vigente | Regem este inventário |
| `docs/governanca/MAPA-DOCUMENTAL.md` | Mapa de fontes canônicas | própria | vigente | **Atualizar**: seção `docs/migracao-hyperframes/` |
| `docs/governanca/CI-E-PRS.md` | CI, gates, padrão de PRs | própria | vigente | **Atualizar**: workflow de smoke HyperFrames (F14) |

## Decisões arquiteturais (`docs/decisoes/`)

| Decisão | Assunto | Situação | Impacto / ação |
| --- | --- | --- | --- |
| `MKT-VIDEO-001` | Produção modular; "HyperFrames não foi adotado" | histórico (com nota 27/11) | Contradição histórica preservada; nota aponta para MKT-VIDEO-003 |
| `MKT-PIPELINE-001` | Pipeline por beats/contratos; adaptadores | histórico (com nota 27/11) | Define o seam do adaptador; nota aponta para MKT-VIDEO-003 |
| `MKT-PLATFORM-001` | Núcleo multiprojeto sem marca | vigente | Adaptador HyperFrames fica fora do núcleo neutro (vendor em adaptador) |
| `MKT-VIDEO-002` | VIDEO CLEAN / narração separada | vigente | **Regra de ouro do novo motor**; sem alteração |
| `MKT-BRAND-001` | Marca Salão / Meu Salão / Studio Bella | vigente | Identidades preservadas nas composições |
| `MKT-VIDEO-003` | HyperFrames motor principal | vigente (nova) | Decisão canônica desta migração |

## Arquitetura e operação

| Caminho | Finalidade | Categoria | Situação | Impacto / ação |
| --- | --- | --- | --- | --- |
| `docs/arquitetura-fabrica.md` | Arquitetura da fábrica (preset_runner, factory_cli, pipeline) | própria | vigente | **Atualizar** com o motor HyperFrames quando o adaptador estabilizar |
| `docs/guia-operacional-titular.md` | Operação pelo titular | própria | vigente | **Atualizar**: caminho HyperFrames no Studio |
| `platform/README.md` | Núcleo TS de contratos; "nenhum renderizador implementado" | própria | vigente (desatualizada pós-27/11) | **Atualizar**: o adaptador HyperFrames passa a existir |
| `tools/produce/README.md` | Guias de produção (preflight, backup, verificação de entrega) | própria | vigente | **Atualizar**: guia do adaptador HyperFrames |
| `tools/render/README.md` | Escopo do render local e garantias transacionais | própria | vigente | Preservado como FALLBACK; citar no RUNBOOK |

## Contratos, tenants e templates

| Caminho | Finalidade | Categoria | Situação | Impacto / ação |
| --- | --- | --- | --- | --- |
| `platform/src/*.ts` + `platform/schemas/` | Contratos neutros e schemas | própria | vigente | Preservados; adaptador os consome (ver CONTRATOS-E-ADAPTADORES) |
| `tenants/*/brand-kit.json`, `guardrails.json` | Identidade e regras por tenant | própria | vigente | Fonte de tokens/guardrails das composições |
| `tenants/marca-salao/frame.md` | Design system de vídeo (frontmatter normativo) | própria | vigente (v2, 27/11) | **Consumir por máquina** no adaptador (F5/F6) |
| `templates/story_reel_vertical/`, `templates/youtube_horizontal/` | Projetos HyperFrames 0.8.126 de demonstração | terceiros/gerado | histórico | **Não editar**; referência técnica apenas |
| `templates/reel_link_overlay/` | Overlay 9:16 + `edit_link_reel.py` | terceiros/gerado | histórico | Prova de conceito viva da CLI; não editar |
| `.agents/skills/` (25 skills) + `skills-lock.json` | Skills HyperFrames (upstream `cfaefdc`) | terceiros | vigente | Versionadas; atualização via procedimento oficial |
| `.agents/plugins/egm/` | Bundle EGM | terceiros | vigente | Intocado por esta migração |

## Campanhas e histórico

| Caminho | Situação | Impacto / ação |
| --- | --- | --- |
| `02-reels-shorts/ns-001-*` (v1…v2.8, editorial-v2, v3) | vigente/histórico | Preservar; base da comparação v2/v3 × HyperFrames (F13) |
| `04-legendas/ns001_roteiro_001_*` | vigente/histórico | Preservar; narração TXT segue no padrão |
| `docs/historico/2026-11-24-operacao-resultado-03-ns001.md` | histórico | Publicação NS-001 reprovada; sem efeito na HF-001 |
| `docs/auditorias/NS-001-PRONTIDAO-COMERCIAL.md` | histórico | Claims/guardrails seguem vigentes nas novas peças |

## Não versionado (local por estação) — preservar, não commitar

- `<RAIZ>/.workspace/` (worktrees op24/op26/ns001v2/hf001, tools/ffmpeg, tmp/hf001).
- `node_modules/` (excluído localmente via `.git/info/exclude`).
- `.claude/`, `agent/` (symlinks por harness gerados pelo instalador de skills).
- No **checkout principal** (main): `tools/render_local.py` modificado (fix de range
  libass/FFmpeg 9, não commitado), `skills-lock.json` v1 (web-design-guidelines),
  `.qoder/skills/`, `editorial-v2/` e TXTs/SRTs v2 não rastreados — **não tocar**;
  registrados como trabalho em curso de outra sessão.

## Lacunas documentais (resumo; detalhe em INVENTARIO-FUNCIONAL.md)

1. `platform/README.md` descreve "nenhum renderizador implementado" — desatualizado após
   a instalação; atualizar na entrega do adaptador.
2. Não havia documento descrevendo a fila do Studio para agentes externos além do código
   (`tools/studio_queue.py`) — o RUNBOOK desta migração passa a cobrir o caminho HyperFrames.
3. `tenants/*/campaigns/README.md` com índices conflitantes (backlog P2 pré-existente;
   não agravado por esta migração).
