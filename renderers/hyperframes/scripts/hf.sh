#!/usr/bin/env bash
# Wrapper portavel da CLI HyperFrames com caches confinados a <RAIZ>/.workspace/tmp/hf001.
# Uso: bash renderers/hyperframes/scripts/hf.sh <comandos...>   (ex.: doctor --json)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config/env.sh
source "$SCRIPT_DIR/../config/env.sh"
cd "$SCRIPT_DIR/.."
exec npx --no-install hyperframes "$@"
