# Devlog — Etapa 5B, Agente 1 de 4 (Bootstrap FFmpeg e Fix de Path do static_cards)

## Contexto

- Repositório principal: `marcasalao-marketing` (checkout principal resolvido via
  `git rev-parse --git-common-dir`).
- Worktree isolada: `.workspace/worktrees/etapa5b-agente1`.
- Branch: `codex/etapa5b-agente1-ffmpeg-static-fix` (criada a partir de `main`, commit `edd56e8`).
- Base de leitura: `contexto_projeto.md`, `tools/build_video.py`,
  `tools/static_cards.py`, `tools/tests/test_static_cards.py`.
- Território exclusivo (editado/criado): `tools/bootstrap_ffmpeg.py`,
  `tools/tests/test_bootstrap_ffmpeg.py`, `tools/static_cards.py`,
  `tools/tests/test_static_cards.py`, `.workspace/devlogs/etapa5-agente1b.md`.
- Não tocado: `contexto_projeto.md`, `tools/build_video.py`,
  `01-insta-stories/deliveries/**`, worktrees dos agentes 2, 3 e 4.

## Ambiente (pré-condição)

- `ffmpeg`/`ffprobe` ausentes no PATH e em `.workspace/tools/ffmpeg` no início.
- Windows: worktree falhou no primeiro `git worktree add` por "Filename too long"
  (path longo em `platform/examples/...`). Recriada com
  `git -c core.longpaths=true worktree add` (override por comando; config persistente
  não alterada).
- `.git/info/exclude` recebeu exclusões locais: `.workspace/worktrees/`,
  `.workspace/tools/`, `.workspace/tmp/`, `.workspace/archives/` (devlogs permanecem
  rastreáveis, como já ocorria com `etapa5-agente1.md`).

## Implementações

### 1. `tools/bootstrap_ffmpeg.py` — instalador portátil idempotente (100% stdlib)

API `ensure_ffmpeg_tools(root=".", force=False) -> dict` e CLI
`python tools/bootstrap_ffmpeg.py [--check-only] [--force] [--json] [--root DIR]`.

- Resolve `MAIN_ROOT` via `git rev-parse --git-common-dir` (funciona igual no checkout
  principal e em worktrees), instalando em `<MAIN_ROOT>/.workspace/tools/ffmpeg/`
  (compartilhado por todas as worktrees).
- Detecção: procura `ffmpeg`/`ffprobe` em `.workspace/tools/ffmpeg` e no PATH,
  validando ambos com `-version`. Se já operacionais e sem `--force`, retorna
  `status: already_available` sem baixar.
- Download Windows: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`
  via `urllib.request`, com verificação de `Content-Length` (evita zip truncado
  silencioso) e validação de integridade CRC (`zipfile.testzip`) antes de extrair.
- Extração por **basename** (`staging/<ffmpeg.exe|ffprobe.exe>`) — contém qualquer
  path traversal do zip. Promoção atômica com `os.replace` (staging em
  `<MAIN_ROOT>/.workspace/tmp/ffmpeg-bootstrap`, mesmo volume).
- Zip único por execução dentro do staging (evita corrida entre processos que
  compartilhem o mesmo caminho temporário).
- Limpeza de temporários no `finally`; nunca versiona `.exe`/`.zip` (verificado via
  `git check-ignore`, reportado como `gitignored: true`).

### 2. Correção de path do `static_cards.py` (Errno 22 em paths longos)

Causa raiz: `DELIVERIES_REL`/`NARRATION_REL` usavam barra normal (`/`) e, ao serem
combinados via `os.path.join`, geravam caminhos mistos (`\` + `/`).
`render_local.fs_path` prefixa `\\?\` em caminhos longos, e o prefixo estendido do
Windows rejeita `/` (`Errno 22 EINVAL`).

Correções:
- Constantes com separadores nativos: `os.path.join("01-insta-stories", "deliveries")`
  e `os.path.join("02-reels-shorts", "deliveries")`.
- Helper `_fs()` que aplica `os.path.normpath` antes de `render_local.fs_path`,
  garantindo que o prefixo `\\?\` receba separadores nativos.
- Todas as chamadas de `fs_path` no módulo redirecionadas para `_fs`.
- `main()`: `--root` resolvido com `os.path.realpath(os.path.abspath(...))`.
- Teste de regressão `test_caminhos_os_nativos_e_normpath` em
  `tools/tests/test_static_cards.py`. Os dois testes de CLI agora passam `--root ROOT`
  explícito ao subprocesso.

### 3. `tools/tests/test_bootstrap_ffmpeg.py` — 8 testes (herméticos + real)

1. `already_available` quando os binários existem (sem baixar).
2. Extração + promoção atômica de um `.zip` simulado (`ffmpeg-*-essentials_build/bin/`).
3. `--check-only` retorna `1` quando ausente e `0` quando presente.
4. Contenção de caminho (membros maliciosos gravados só pelo basename).
5. Limpeza automática dos temporários após instalar.
6. CLI `--json` devolve payload estruturado válido.
7. Detecção real no ambiente (pula antes da instalação; valida depois).
8. (contagem inclui 1..7 + 8 conforme acima.)

Downloads mockados; binários simulados em `TemporaryDirectory` sob `.workspace/tmp`
(regra de armazenamento da raiz).

## Resultados

- `python -m unittest tools.tests.test_bootstrap_ffmpeg tools.tests.test_static_cards -v`
  → **21 testes, OK, 0 falhas, 0 erros, 0 skip**.
- `static_cards` isolado → 13/13 OK.
- Instalação real: `python tools/bootstrap_ffmpeg.py --json` →
  `status: installed`, ffmpeg **9.1-essentials_build**, sha256 do zip
  `b9bbbb3acece000cbeec994f856649354e52c773807841e78908374b24d658fd`.
- `ffmpeg -version` / `ffprobe -version` confirmados manualmente.
- `--check-only` → `status: available`, exit 0.

## Incidente e correção (transparência)

A primeira instalação falhou com `BadZipFile: Bad CRC-32`. Diagnóstico: o harness,
ao "mover para background" um comando que excedeu o timeout, gerou **duas execuções
concorrentes** que escreveram o mesmo `zip_path`, corrompendo o pacote (tamanho
correto, bytes errados). Correções aplicadas no próprio bootstrap (zip único por
staging + verificação de Content-Length + CRC) e processo órfão encerrado; a
re-execução em execução única instalou corretamente.

## Observações

- `tools/build_video.py` resolve ffmpeg apenas por `PATH` (fora do território deste
  agente). `tools/derivative_formats.py` já faz fallback para
  `.workspace/tools/ffmpeg`. Consumidores que dependam só de PATH precisariam expor
  esse diretório no PATH — não alterado por política de não mudar PATH permanente.
- Este devlog será sincronizado em `contexto_projeto.md` na consolidação (devlog_sync).