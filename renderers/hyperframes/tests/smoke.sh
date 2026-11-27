#!/usr/bin/env bash
# Smoke test da instalacao HyperFrames (HF-001):
# scaffold -> check -> render draft -> ffprobe (exatamente 1 stream de video, 0 de audio).
# Uso: bash renderers/hyperframes/tests/smoke.sh
# Sai 0 quando passa; imprime PASS/FAIL e o caminho do MP4.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config/env.sh
source "$SCRIPT_DIR/../config/env.sh"
HF_BIN="$SCRIPT_DIR/../node_modules/.bin/hyperframes"
if [ ! -f "$HF_BIN" ]; then
  echo "FAIL: binario hyperframes ausente. Rode npm install em renderers/hyperframes." >&2
  exit 1
fi

SMOKE_DIR="$HF001_TMP/smoke-run"
rm -rf "$SMOKE_DIR"
mkdir -p "$SMOKE_DIR"

echo "== init =="
"$HF_BIN" init "$SMOKE_DIR/proj" --resolution portrait >/dev/null
cd "$SMOKE_DIR/proj"

echo "== check =="
"$HF_BIN" check >/dev/null

echo "== render draft =="
"$HF_BIN" render --quality draft --output "$SMOKE_DIR/out.mp4" >/dev/null

echo "== ffprobe =="
FFPROBE_BIN="$(command -v ffprobe || echo "$HF001_FFMPEG_DIR/ffprobe")"
PROBE_JSON="$("$FFPROBE_BIN" -v error -show_entries stream=codec_type,width,height -show_entries format=duration -of json "$SMOKE_DIR/out.mp4")"
python - "$SMOKE_DIR/out.mp4" "$PROBE_JSON" <<'PY'
import json, sys
path, probe = sys.argv[1], json.loads(sys.argv[2])
streams = [s for s in probe["streams"]]
video = [s for s in streams if s["codec_type"] == "video"]
audio = [s for s in streams if s["codec_type"] == "audio"]
assert len(video) == 1, f"esperado 1 stream de video, achei {len(video)}"
assert len(audio) == 0, f"esperado 0 streams de audio (VIDEO CLEAN), achei {len(audio)}"
assert video[0]["width"] == 1080 and video[0]["height"] == 1920, f"geometria inesperada: {video[0]}"
dur = float(probe["format"]["duration"])
assert 9.0 <= dur <= 11.0, f"duracao inesperada: {dur}"
print(f"PASS: {path} — h264 {video[0]['width']}x{video[0]['height']}, {dur:.1f}s, 0 faixas de audio")
PY
