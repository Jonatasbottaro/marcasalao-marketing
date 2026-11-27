#!/usr/bin/env bash
# Teste dedicado de determinismo do adaptador HyperFrames (HF-001, F14; pendencia
# do criterio F6): mesmo pedido + mesma versao pinada -> dois renders
# independentes produzem o mesmo video. Evidencia em duas camadas: hash SHA-256
# do arquivo inteiro E hash SHA-256 de frames-chave extraidos em instantes
# fixos (FFmpeg). Sai 0 somente se todas as camadas conferirem.
# Uso: bash renderers/hyperframes/tests/determinism.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../config/env.sh
source "$SCRIPT_DIR/../config/env.sh"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

REQUEST="$ROOT/tools/produce/examples/marca-salao-social-reel.video-request.json"
RUN_DIR="$ROOT/.workspace/tmp/hf001/determinism/run-$$"
mkdir -p "$RUN_DIR"

echo "== midia sintetica do pedido =="
python "$ROOT/tools/make_request_media.py" --input "$REQUEST" --root "$ROOT" >/dev/null

for i in 1 2; do
  echo "== render independente $i (draft) =="
  python "$ROOT/tools/render_hyperframes.py" \
    --input "$REQUEST" \
    --root "$ROOT" \
    --profile instagram-reels-video \
    --quality draft \
    --workdir "$RUN_DIR/composicao-$i" \
    --out "$RUN_DIR/video-$i.mp4" > "$RUN_DIR/veredito-$i.json"
done

echo "== comparacao: arquivo inteiro + frames-chave =="
python - "$RUN_DIR" <<'PY'
import hashlib, json, shutil, subprocess, sys
from pathlib import Path

run = Path(sys.argv[1])
first, second = run / "video-1.mp4", run / "video-2.mp4"

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verdict(name):
    with open(run / f"veredito-{name}.json", encoding="utf-8") as handle:
        return json.load(handle)

v1, v2 = verdict(1), verdict(2)
assert v1.get("ok") is True and v2.get("ok") is True, "algum veredito nao ok"
assert v1.get("durationSeconds") == v2.get("durationSeconds"), \
    f"duracoes divergem: {v1.get('durationSeconds')} x {v2.get('durationSeconds')}"

file_hash_1, file_hash_2 = sha256(first), sha256(second)
assert file_hash_1 == file_hash_2, \
    f"MP4 divergem: {file_hash_1} x {file_hash_2}"

ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
if not ffmpeg:
    import os
    _ffdir = os.environ.get("HF001_FFMPEG_DIR", "")
    if _ffdir:
        for _name in ("ffmpeg", "ffmpeg.exe"):
            _cand = os.path.join(_ffdir, _name)
            if os.path.isfile(_cand):
                ffmpeg = _cand
                break
assert ffmpeg, "ffmpeg ausente no PATH (env.sh deveria expor o portavel)"

# Frames-chave: meio de cada cena do pedido de exemplo (4+6+4 s). Instantes
# fixos, depois das entradas e antes do fade-out do ultimo beat.
timestamps = ["2.0", "7.0", "13.0"]
frame_hashes = {}
for label, video in (("1", first), ("2", second)):
    hashes = []
    for t in timestamps:
        out = run / f"frame-{label}-{t}.png"
        subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-ss", t, "-i", str(video),
             "-frames:v", "1", str(out)],
            check=True)
        hashes.append(sha256(out))
    frame_hashes[label] = hashes
assert frame_hashes["1"] == frame_hashes["2"], \
    f"frames-chave divergem: {frame_hashes['1']} x {frame_hashes['2']}"

print(f"PASS determinismo: {first.name} == {second.name}")
print(f"  SHA-256 arquivo:  {file_hash_1}")
for t, h in zip(timestamps, frame_hashes["1"]):
    print(f"  SHA-256 frame {t}s: {h}")
print(f"  duracao: {v1.get('durationSeconds')}s nos dois renders")
PY
