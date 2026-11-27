# renderers/hyperframes — Runtime HyperFrames do Marca Salão Marketing

Motor principal de composição e renderização audiovisual (decisão HF-001 / MKT-VIDEO-003).
A fábrica existente (orquestração Python, contratos `platform/`, fila do Video Studio,
biblioteca de mídia, revisão e empacotamento) é preservada; este diretório é a camada
HyperFrames que ela passa a acionar.

## Versão instalada

| Pacote | Versão exata | Papel |
| --- | --- | --- |
| `hyperframes` | 0.9.103 | CLI: init, lint, check, preview, snapshot, render |
| `@hyperframes/producer` | 0.9.103 | API programática de jobs de render (fila) |

- Data da instalação: 27/11/2026.
- Origem: registry npm (`registry.npmjs.org`); repositório `heygen-com/hyperframes`;
  documentação `https://hyperframes.heygen.com` (índice `llms.txt`).
- Versões fixadas em `package.json` + `package-lock.json`. Não usar `latest` em produção.
- Templates históricos (`templates/`) pinam `0.8.126` e permanecem intocados (terceiros).
- Telemetria desativada (`hyperframes telemetry disable`).

## Requisitos

- Node.js ≥ 22 (validado em v26.13.1, Windows 10 x64).
- FFmpeg + FFprobe: o projeto usa o portátil em `<RAIZ>/.workspace/tools/ffmpeg/`
  (por estação); `config/env.sh` o coloca no PATH do processo. Em CI Ubuntu, o FFmpeg
  do sistema serve.
- Chrome: a CLI baixa o `chrome-headless-shell` gerenciado na primeira execução
  (`hyperframes browser ensure`), mantendo saída reproduzível entre máquinas.

## Portabilidade (AGENTS.md)

`config/env.sh` confina, por processo, todos os caches e temporários em
`<RAIZ>/.workspace/tmp/hf001/`:

- `npm_config_cache`, `TEMP`/`TMP`/`TMPDIR`, `PUPPETEER_CACHE_DIR`, `XDG_CACHE_HOME`;
- `HOME`/`USERPROFILE` redirecionados para o mesmo diretório (cobre `~/.cache/hyperframes`);
- FFmpeg portátil no `PATH` quando existir;
- `HYPERFRAMES_SKIP_SKILLS=1`: skills ficam versionadas em `.agents/skills/`, o `init`
  não consulta o GitHub.

`<RAIZ>` é resolvido em tempo de execução via `git rev-parse --git-common-dir`
(funciona dentro de worktrees; não fixa caminho de máquina). `node_modules/` é local
por estação, ignorado via `.git/info/exclude`.

## Uso

```bash
# CLI global (doctor, browser, catalog, docs):
bash renderers/hyperframes/scripts/hf.sh doctor --json

# Comandos dentro de um projeto de composição (lint/check/render/snapshot):
bash renderers/hyperframes/scripts/hf-project.sh <dir-do-projeto> check
bash renderers/hyperframes/scripts/hf-project.sh <dir-do-projeto> render --quality draft --output out.mp4
```

Projetos de composição vivem em `compositions/<tenant>/<campanha>/` (scaffold via
`hf.sh init`, scripts pinando `hyperframes@0.9.103`). O adaptador da fábrica fica em
`adapter/` (contratos `platform/` → projeto HyperFrames → render → veredito JSON).

## Adaptador (F6)

Cadeia: `tools/render_hyperframes.py` (entrada Python; compila o VideoRequest pela
ponte `render_bridge.mjs`) → `scripts/hf-adapter.sh` (env confinado) →
`adapter/hf_adapter.mjs` (orquestrador) com:

- `adapter/tenant.mjs` — carrega `frame.md` (frontmatter normativo), `brand-kit.json`
  e `guardrails.json` do tenant; valida caption/title/narration contra as alegações
  proibidas **antes** do render (violação aborta com erro estruturado);
- `adapter/compose.mjs` — materializa o projeto de composição (HTML `data-*`,
  timeline GSAP seekable, headerOverlay, textos gráficos, zoom/framing por cena,
  `narracao.txt` separado) e copia a mídia para `assets/` com confinamento de caminho;
- verificação `ffprobe` na saída: 1 stream de vídeo, **0 streams de áudio**
  (VIDEO CLEAN), geometria e duração conforme o plano.

```bash
# producao completa a partir de um pedido VideoRequest:
python tools/render_hyperframes.py --input <pedido.video-request.json> \
  --profile instagram-reels-video --quality draft
# apenas compor e rodar o check:
python tools/render_hyperframes.py --input <pedido.video-request.json> --skip-render
```

Decisão CLI × API: o adaptador usa o **CLI pinado** (spawn do módulo
`hyperframes/bin/hyperframes.mjs`) — caminho único para `check` + `render`,
isolamento de processo e códigos de saída estáveis. A API
`@hyperframes/producer` (`createRenderJob`/`executeRenderJob`) permanece instalada
como opção para progresso fino da fila (F8); não há compromisso de adoção.

Smoke do adaptador: `tests/adapter-smoke.sh` (positivo: render draft + ffprobe;
negativo: claim proibida aborta antes do render).

## VIDEO CLEAN (MKT-VIDEO-002)

- Composições mudas: sem `<audio>`, vídeos `muted`, sem narração/TTS/música no editor.
- Render sem faixa de áudio (o smoke test comprova: 1 stream h264, 0 streams de áudio).
- Sem legendas narrativas queimadas; SRT somente sob pedido expresso.
- Textos gráficos editoriais (títulos, chips, CTA) pertencem à composição.
- Narração entregue em TXT separado (`04-legendas/`), pronta para ferramenta externa.

## Smoke test

`tests/smoke.sh` — scaffold → check → render draft → ffprobe (0 faixas de áudio).
Evidência da instalação (27/11/2026): MP4 h264 1080×1920, 10.0 s, 0 streams de áudio,
render local em 22.7 s (software gpu, capture screenshot), caches confinados.

`tests/adapter-smoke.sh` — adaptador ponta a ponta (27/11/2026): pedido real de
exemplo → composição → check → render draft → ffprobe (h264 1080×1920, 14.0 s,
0 streams de áudio) + caso negativo de guardrails ("24h", "agenda sempre cheia"
abortam antes do render com `GUARDRAILS_VIOLATION`).
