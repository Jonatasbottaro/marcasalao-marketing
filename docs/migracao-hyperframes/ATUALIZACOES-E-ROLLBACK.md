# Atualizações e rollback — HF-001

## Política de versões

- O projeto usa **HyperFrames 0.9.103, pinado exato** em
  `renderers/hyperframes/package.json` e nos scripts dos projetos de composição.
  O pin nunca avança sozinho; render é reproduzível entre estações.
- Skills HyperFrames ficam vendadas em `.agents/skills/` com
  `skills-lock.json` v2 (upstream `heygen-com/hyperframes` commit `cfaefdc` +
  hashes por skill). Atualização somente pelo procedimento oficial
  (`npx skills add heygen-com/hyperframes --all`), nunca por cópia manual.
- Chrome de render é **pinado pelo CLI** (build específica, cache em
  `<RAIZ>/.workspace/tmp/hf001/puppeteer/`): existe para que o pixel de saída não
  deriva entre máquinas. Não trocar por Chrome do sistema.
- FFmpeg/FFprobe portáveis em `.workspace/tools/ffmpeg/` (gyan.dev essentials) —
  mesma versão em todas as estações que renderizarem.

## Procedimento de atualização (deliberado, nunca automático)

1. Registrar a intenção e a versão-alvo (issue/handoff).
2. Na branch técnica (nunca direto na `main`): atualizar o pin em
   `renderers/hyperframes/package.json`, instalar e rodar o smoke completo
   (`renderers/hyperframes/tests/smoke.sh`).
3. Re-renderar **uma** composição de referência e comparar snapshots com a versão
   anterior (o `check` verde garante validação, não paridade de pixel).
4. Atualizar skills pelo procedimento oficial e conferir o lock.
5. Atualizar a tabela de versões do `renderers/hyperframes/README.md` e registrar
   em [EVIDENCIAS.md](EVIDENCIAS.md).
6. Commit na branch técnica + PR rascunho; a versão só vira padrão depois de
   aprovada e integrada.

## Rollback

### Rollback do motor (produção volta ao FFmpeg)

- Nada precisa ser desinstalado: o caminho FFmpeg (`render_pipeline.py`/
  `render_local.py` com `--clean`) permanece instalado e testado.
- Ação: parar de submeter itens `hyperframes` (manifest volta a apontar o adaptador
  local) e produzir pelo caminho existente. Registrar a decisão no handoff.
- Itens já concluídos no HyperFrames **não** são re-renderizados retroativamente.

### Rollback da branch (estado do repositório)

- A migração vive em branch técnica (`codex/hyperframes-core-migration`) enviada ao
  remoto; `main` permanece intocada. Rollback de repositório = não fazer merge.
- Worktree da tarefa: `git worktree remove` + `git worktree prune` (nunca `rm -rf`).
- Commits da operação ficam preservados no remoto — reversão é por decisão nova
  (revert explícito), nunca por rebase/force.

### Rollback do runtime local (estação)

- Remover `renderers/hyperframes/node_modules/` e os caches em
  `<RAIZ>/.workspace/tmp/hf001/` (npm-cache, temp, puppeteer, xdg-cache, home).
- O Chrome pinado (~717 MB) pode ser preservado se outra atualização vier em
  seguida; caso contrário `hf.sh browser clear` remove o download.
- Nada disto afeta a fábrica legada ou o render local FFmpeg.

## O que nunca é objeto de rollback

- Campanhas históricas (NS-001 v1…v3) e seus roteiros: patrimônio.
- Fábrica legada (`preset_runner.py`/`factory_cli.py`): congelada por decisão.
- Templates históricos (`templates/`): referência, não se reverte nada neles.
- Regras de governança (AGENTS.md, guardrails, VIDEO CLEAN): a migração não as
  altera, então não há "voltar" delas.
