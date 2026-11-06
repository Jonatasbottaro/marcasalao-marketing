#!/usr/bin/env bash
# Executa um comando do gate de contratos publicando saida, resumo e codigo de saida.
#
# Uso: bash scripts/gate-step.sh <log> <rotulo> <comando...>
#
# O runner chama cada passo com `bash --noprofile --norc -e -o pipefail`. Sob errexit, um
# pipeline com tee que falha encerra o passo na hora: a captura do codigo e o resumo depois
# dele eram inalcancais. Aqui o errexit so e suspenso durante o pipeline, os dois status do
# pipeline sao lidos por PIPESTATUS e o comando vence o tee no codigo devolvido.
set -o pipefail

log=$1
label=$2
shift 2

mkdir -p "$(dirname "$log")"

set +e
"$@" 2>&1 | tee "$log"
# PIPESTATUS e substituido antes da execucao da linha: a captura dos dois status precisa
# acontecer em um unico comando, porque o primeiro `var=${PIPESTATUS[0]}` ja reinicia o array.
pipeline_codes=("${PIPESTATUS[@]}")
set -e

cmd_code=${pipeline_codes[0]}
tee_code=${pipeline_codes[1]:-0}

linha="${label}: codigo de saida ${cmd_code} (tee ${tee_code})"
echo "$linha"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  echo "$linha" >> "$GITHUB_STEP_SUMMARY"
fi

if [ "$cmd_code" -ne 0 ]; then
  exit "$cmd_code"
fi

# Uma falha do tee nunca pode virar sucesso silencioso.
exit "$tee_code"
