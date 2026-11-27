#!/usr/bin/env bash
# Smoke test do adaptador HyperFrames (HF-001, F6):
# compila um VideoRequest real de exemplo -> materializa composicao -> check ->
# render draft -> ffprobe (1 video, 0 audio) -> veredito JSON; e o caso negativo
# de guardrails (claim proibida aborta antes do render).
# Uso: bash renderers/hyperframes/tests/adapter-smoke.sh
# Sai 0 quando passa; imprime PASS/FAIL.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config/env.sh
source "$SCRIPT_DIR/../config/env.sh"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

REQUEST="$ROOT/tools/produce/examples/marca-salao-social-reel.video-request.json"
# Workdir dentro do checkout sob teste (ROOT); HF001_TMP (env) continua valendo
# para caches de npm/Chrome/temp do runtime. Diretorio unico por execucao: o
# Chrome do render anterior pode ainda segurar o diretorio por instantes.
RUN_DIR="$ROOT/.workspace/tmp/hf001/adapter-smoke/run-$$"
mkdir -p "$RUN_DIR"

echo "== midia sintetica do pedido =="
python "$ROOT/tools/make_request_media.py" --input "$REQUEST" --root "$ROOT" >/dev/null

echo "== adaptador: compose + check + render draft =="
python "$ROOT/tools/render_hyperframes.py" \
  --input "$REQUEST" \
  --root "$ROOT" \
  --profile instagram-reels-video \
  --quality draft \
  --workdir "$RUN_DIR/composicao" \
  --out "$RUN_DIR/video.mp4" > "$RUN_DIR/veredito.json"
python - "$RUN_DIR/veredito.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as handle:
    verdict = json.load(handle)
assert verdict.get('ok') is True, f'verdeito nao ok: {verdict}'
assert verdict.get('adapter') == 'hyperframes', verdict
assert verdict.get('audioStreams') == 0, f"esperado 0 faixas de audio (VIDEO CLEAN): {verdict.get('audioStreams')}"
assert verdict.get('videoStreams') == 1, verdict
assert verdict.get('geometry') == {'width': 1080, 'height': 1920}, verdict.get('geometry')
dur = verdict.get('durationSeconds')
assert dur and 13.5 <= dur <= 14.5, f'duracao inesperada: {dur}'
print(f"PASS adaptador: {verdict['outputPath']} — {verdict['geometry']['width']}x{verdict['geometry']['height']}, {dur:.1f}s, 0 faixas de audio")
PY

echo "== guardrails: claim proibida aborta antes do render =="
python - "$REQUEST" "$RUN_DIR/pedido-proibido.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as handle:
    request = json.load(handle)
request['scenes'][0]['caption'] = 'Agenda sempre cheia, 24h sem faltas'
request['id'] = 'marca-salao-guardrails-negativo'
with open(sys.argv[2], 'w', encoding='utf-8', newline='\n') as handle:
    json.dump(request, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
PY
set +e
python "$ROOT/tools/render_hyperframes.py" \
  --input "$RUN_DIR/pedido-proibido.json" \
  --root "$ROOT" \
  --profile instagram-reels-video \
  --quality draft \
  --workdir "$RUN_DIR/composicao-negativa" \
  --out "$RUN_DIR/video-proibido.mp4" > "$RUN_DIR/veredito-negativo.json" 2>"$RUN_DIR/erro-negativo.txt"
NEG_STATUS=$?
set -e
if [ "$NEG_STATUS" -eq 0 ]; then
  echo "FAIL: pedido com claim proibida nao foi bloqueado" >&2
  exit 1
fi
python - "$RUN_DIR/veredito-negativo.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as handle:
    verdict = json.load(handle)
assert verdict.get('ok') is False, verdict
assert verdict.get('failureCode') == 'GUARDRAILS_VIOLATION', verdict
inner = verdict.get('adapterVerdict') or {}
assert inner.get('failureCode') == 'GUARDRAILS_VIOLATION', inner
terms = {v.get('term') for v in inner.get('violations', [])}
assert '24h' in terms and 'agenda sempre cheia' in terms, terms
print(f"PASS guardrails: violacoes detectadas antes do render: {sorted(terms)}")
PY

echo "PASS adapter-smoke completo"
