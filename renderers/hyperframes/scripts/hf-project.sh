#!/usr/bin/env bash
# Executa a CLI HyperFrames (binario da instalacao central em renderers/hyperframes)
# dentro de um projeto de composicao, com caches confinados a <RAIZ>/.workspace/tmp/hf001.
# Uso: bash renderers/hyperframes/scripts/hf-project.sh <dir-do-projeto> <comandos...>
#      ex.: bash renderers/hyperframes/scripts/hf-project.sh compositions/marca-salao/x check
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config/env.sh
source "$SCRIPT_DIR/../config/env.sh"
HF_BIN="$SCRIPT_DIR/../node_modules/.bin/hyperframes"
if [ ! -x "$HF_BIN" ] && [ ! -f "$HF_BIN" ]; then
  echo "ERRO: binario hyperframes nao encontrado em $HF_BIN. Rode npm install em renderers/hyperframes." >&2
  exit 1
fi
PROJECT_DIR="$(cd "$1" && pwd)"; shift
cd "$PROJECT_DIR"
exec "$HF_BIN" "$@"
