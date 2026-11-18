# Elephant-Goldfish Model (EGM) no repositório

Este documento registra a instalação canônica do **Elephant-Goldfish Model (EGM)** dentro do repositório `marcasalao-marketing`, preservando a portabilidade entre computadores, IDEs e agentes de código (*harnesses*) exigida em `AGENTS.md`.

## Proveniência

- **Origem upstream:** `https://github.com/google/elephant-goldfish-model`
- **Versão do plugin:** `0.1.1`
- **Commit upstream fixado:** `70406c4d22cc7ea8299637c2c5b44625c48b3f08`
- **Licença:** `Apache-2.0` (preservada em `.agents/plugins/egm/LICENSE`)
- **Data da instalação:** `2026-11-17`

## Estrutura instalada em `<RAIZ>`

- `.agents/plugins/egm/` — pacote completo de runtime do EGM (fonte única, sem duplicação de texto de skills):
  - `plugin.json` — manifesto portátil (Agent Plugins 1.0.0), descoberto automaticamente pelo Antigravity.
  - `skills/` — todas as 8 skills oficiais (`egm-bootstrap`, `egm-brainstorm`, `egm-draft`, `egm-drift-report`, `egm-lite`, `egm-resolve`, `egm-review`, `egm-review-loop`) com seus ícones, metadados e referências.
  - `agents/` — todas as 10 personas/orquestradores (`bootstrap_orchestrator`, `codebase_details`, `comprehension`, `design_critic`, `implementation_readiness`, `inventive_catalyst`, `structural`, `style`, `synthesizer`, `zoom_out`).
  - `resources/` — `execution_instructions.md` e os 5 padrões de documento em `resources/document_standards/`.
  - `docs/` — documentação oficial de harnesses (`harnesses.md`, `codex.md`, `claude.md`, `opencode.md`, `cursor.md`, `copilot.md`, `muse.md`, `getting_started.md`).
  - `.codex-plugin/plugin.json`, `.claude-plugin/`, `.cursor-plugin/` — manifestos e adaptadores de compatibilidade por host.
  - `adapters/opencode/install.py` — instalador experimental oficial para OpenCode V1.
- `.agents/plugins/marketplace.json` — catálogo de workspace apontando `"source": "./egm"` para o pacote canônico.
- `docs/designs/` — diretório versionado para especificações aprovadas (`README.md`, `SITEMAP.md` e este guia).
- `.workspace/tmp/egm/` — diretório padrão de rascunhos, briefs intermediários e relatórios temporários (`EGM artifact directory: .workspace/tmp/egm`), mantido dentro de `<RAIZ>/.workspace/` e fora do Git.
- `tools/verify_egm_install.py` — verificador offline sem dependências externas.

## Regra de isolamento Goldfish (obrigatória)

O protocolo **Goldfish** exige subagentes em **contexto limpo** (sem histórico da conversa principal). Se um harness não expuser ferramenta de criação de subagente isolado, a revisão Goldfish **deve parar** e informar a limitação — nunca simular revisores Goldfish no mesmo contexto da conversa principal.

## Uso por IDE / Harness

### Antigravity (CLI, App e extensão VS Code)

- Descoberta automática pelo workspace em `.agents/plugins/egm/plugin.json`.
- Comandos: `/egm:egm-brainstorm`, `/egm:egm-draft`, `/egm:egm-review`, `/egm:egm-resolve`, `/egm:egm-review-loop`, `/egm:egm-lite`, `/egm:egm-bootstrap`, `/egm:egm-drift-report`.
- Subagentes: `invoke_subagent`.

### Codex (CLI e Desktop)

- Manifesto de compatibilidade em `.agents/plugins/egm/.codex-plugin/plugin.json` e catálogo em `.agents/plugins/marketplace.json`.
- Também pode ser acionado indicando a skill em `.agents/plugins/egm/skills/<skill>/SKILL.md` e seguindo `.agents/plugins/egm/docs/codex.md`.
- Subagentes: `spawn_agent` com `fork_context: false` (ou `fork_turns: "none"`).

### Claude Code / Claude Cowork

- Manifesto e adaptadores read-only em `.agents/plugins/egm/.claude-plugin/`.
- Guia específico: `.agents/plugins/egm/docs/claude.md`.
- Subagentes: ferramenta `Agent` (Task).

### OpenCode V1 (experimental)

Para gerar um bundle isolado do OpenCode V1 **dentro de `<RAIZ>/.workspace/tools/`** (sem criar arquivos fora da raiz do projeto):

```sh
python .agents/plugins/egm/adapters/opencode/install.py "<RAIZ>/.workspace/tools/egm-opencode"
```

Depois, siga as instruções de execução e limites em `.agents/plugins/egm/docs/opencode.md` (incluindo o requisito de versão `opencode-ai@1.18.29` e `OPENCODE_CONFIG`).

### Qoder, WorkBuddy e DeepSeek Harness (`dsh`)

Esses harnesses não possuem adaptador oficial verificado no upstream do EGM, mas podem usar a mesma instalação canônica do repositório seguindo o contrato registrado em `AGENTS.md`:

1. Ler a skill desejada em `.agents/plugins/egm/skills/<skill>/SKILL.md`.
2. Resolver `agents/*.md`, `resources/document_standards/*.md` e `docs/*.md` sempre contra `.agents/plugins/egm/` (nunca copiar apenas `skills/`).
3. Gravar rascunhos e relatórios intermediários em `.workspace/tmp/egm/` e especificações aprovadas em `docs/designs/`.
4. Para fluxos Goldfish (`egm-brainstorm`, `egm-review`, `egm-review-loop`), disparar subagentes isolados sem histórico da conversa principal; se o harness não garantir esse isolamento, interromper em vez de simular a revisão.

## Verificação offline da instalação

A partir de `<RAIZ>`, execute:

```sh
python tools/verify_egm_install.py
```

O script valida a presença de todas as 8 skills, 10 personas, 5 padrões de documento, manifestos JSON, integridade dos links relativos dentro do bundle, ausência de symlinks e configuração de `EGM artifact directory: .workspace/tmp/egm` em `AGENTS.md` e `CLAUDE.md`.
