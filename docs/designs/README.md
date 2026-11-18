# Especificações aprovadas (EGM — `docs/designs/`)

Este diretório armazena as especificações técnicas e documentos de design **aprovados** gerados ou revisados com o **Elephant-Goldfish Model (EGM)**.

## Separação de diretórios

- **Aprovados e versionados (Git):** `<RAIZ>/docs/designs/` (este diretório, indexado em [`SITEMAP.md`](SITEMAP.md)).
- **Rascunhos, briefs intermediários e relatórios de revisão Goldfish:** `<RAIZ>/.workspace/tmp/egm/` (configurado por `EGM artifact directory: .workspace/tmp/egm` em `AGENTS.md` e `CLAUDE.md`, ignorado localmente pelo Git via `.git/info/exclude`).
- **Pacote canônico do plugin EGM:** `<RAIZ>/.agents/plugins/egm/` (versionado no repositório, portável entre computadores e IDEs).

Consulte [`GUIA-EGM.md`](GUIA-EGM.md) para instruções de uso por agente/IDE (Antigravity, Codex, Claude Code, OpenCode, Qoder, WorkBuddy e DeepSeek Harness) e comando de verificação de integridade.
