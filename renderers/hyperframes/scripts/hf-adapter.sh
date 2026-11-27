#!/usr/bin/env bash
# Executa o adaptador HyperFrames (adapter/hf_adapter.mjs) com caches confinados
# a <RAIZ>/.workspace/tmp/hf001 (HF-001, F6). Uso:
#   bash renderers/hyperframes/scripts/hf-adapter.sh --profile-json <perfil.json> \
#     --root <raiz> --tenant marca-salao --workdir <dir> --out <mp4> [opcoes]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config/env.sh
source "$SCRIPT_DIR/../config/env.sh"
exec node "$SCRIPT_DIR/../adapter/hf_adapter.mjs" "$@"
