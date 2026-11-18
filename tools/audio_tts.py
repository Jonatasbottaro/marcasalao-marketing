"""Gerador modular de trilhas de audio para Shorts (Agente 2 - Etapa 3).

Sincroniza trilhas `.wav` (padrao 30.0 s, 44100 Hz, stereo) para alimentar o
parametro `--audio` do motor `tools/preset_runner.py`, exclusivamente em tenants
cujo `guardrails.audioPolicy.allowAudioTrack` seja `true` (ex.: `multitrack-hub`).

Modos suportados, sem depender de APIs pagas externas:

  * ``ambient-bed``    : sintetiza via FFmpeg ``lavfi`` uma cama sonora limpa e
                         discreta (acorde suave + pulso por tremolo, com
                         fade-in/fade-out e volume normalizado para -22 LUFS).
  * ``narration-bed``  : tenta sintese de voz local (pyttsx3 ou Windows SAPI via
                         PowerShell ``System.Speech``) mixada sobre a cama sonora.
                         Se nenhum motor TTS estiver disponivel, cai de forma
                         automatica e segura para ``ambient-bed``.

Trava de seguranca (sempre, antes de qualquer render):
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=REPO_ROOT, strict=True)
    recusa imediatamente a execucao quando ``allowAudioTrack`` for ``false``
    (como ``marca-salao`` e ``meu-salao``).

Uso (a partir da raiz do checkout):
    python tools/audio_tts.py --tenant multitrack-hub \
        --output .workspace/tmp/audio-mth/bed-30s.wav --duration 30 --mode ambient-bed

    python tools/audio_tts.py --tenant multitrack-hub \
        --output .workspace/tmp/audio-mth/narracao-30s.wav --duration 30 \
        --mode narration-bed --text "Conheca o catalogo do Multitrack Hub."

Uso programatico:
    from tools import audio_tts
    info = audio_tts.generate_audio("multitrack-hub", out_path, duration=30.0,
                                    mode=audio_tts.AMBIENT_BED, root=REPO_ROOT)
    # info["path"] -> passe como audio_path em preset_runner.run_preset_pipeline(...)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_video
import render_local
import tenant_validator

DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 2
DEFAULT_DURATION = 30.0
DEFAULT_LOUDNESS_LUFS = -22.0

AMBIENT_BED = "ambient-bed"
NARRATION_BED = "narration-bed"
SUPPORTED_MODES = (AMBIENT_BED, NARRATION_BED)

_MIN_LOUDNORM_DURATION = 3.0


class AudioTtsError(Exception):
    """Falha controlada do gerador de audio (codigo estavel + mensagem sanitizada)."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


# ---------------------------------------------------------------------------
# Infraestrutura de execucao
# ---------------------------------------------------------------------------
def _run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    """Executa um comando e transforma qualquer falha em AudioTtsError."""
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioTtsError("FFMPEG_TIMEOUT", "comando de audio excedeu o tempo limite") from exc
    except OSError as exc:
        raise AudioTtsError("FFMPEG_NAO_EXECUTAVEL", str(exc)) from exc
    if res.returncode != 0:
        tail = (res.stderr or "").strip()[-400:]
        raise AudioTtsError("FFMPEG_FALHOU", tail or f"codigo {res.returncode}")
    return res


def _resolve_output(root_real: str, output_path: str) -> str:
    if os.path.isabs(output_path):
        return os.path.realpath(output_path)
    return os.path.realpath(os.path.join(root_real, output_path.replace("/", os.sep)))


# ---------------------------------------------------------------------------
# Sintese da cama sonora (ambient-bed) via FFmpeg lavfi
# ---------------------------------------------------------------------------
def _ambient_source_expr() -> str:
    """Acorde suave (A maior com 9a) como soma de senoides de baixa amplitude."""
    return (
        "0.050*sin(2*PI*220*t)"      # A3
        "+0.045*sin(2*PI*277.18*t)"  # C#4
        "+0.045*sin(2*PI*329.63*t)"  # E4
        "+0.030*sin(2*PI*493.88*t)"  # B4 (9a)
    )


def _channel_layout(channels: int) -> str:
    return "stereo" if int(channels) == 2 else "mono"


def _ambient_chain(duration: float, sample_rate: int, channels: int) -> list[str]:
    fade = min(1.8, max(0.3, duration / 6.0))
    layout = _channel_layout(channels)
    chain = [
        "tremolo=f=1.6:d=0.22",
        f"afade=t=in:st=0:d={fade:.3f}",
        f"afade=t=out:st={max(0.0, duration - fade):.3f}:d={fade:.3f}",
    ]
    if duration >= _MIN_LOUDNORM_DURATION:
        chain.append(f"loudnorm=I={DEFAULT_LOUDNESS_LUFS}:TP=-2.0:LRA=11")
    chain.append(
        f"aformat=sample_fmts=s16:channel_layouts={layout}:sample_rates={sample_rate}"
    )
    return chain


def _synthesize_ambient_bed(ffmpeg: str, output_path: str, duration: float,
                            sample_rate: int, channels: int) -> None:
    src = f"aevalsrc={_ambient_source_expr()}:s={sample_rate}:d={duration:.3f}"
    cmd = [ffmpeg, "-y", "-f", "lavfi", "-i", src]
    cmd += ["-af", ",".join(_ambient_chain(duration, sample_rate, channels))]
    cmd += ["-t", f"{duration:.3f}", "-c:a", "pcm_s16le", output_path]
    _run(cmd)


# ---------------------------------------------------------------------------
# Sintese de voz local (narration-bed) com fallback seguro
# ---------------------------------------------------------------------------
def _try_pyttsx3(text: str, out_path: str) -> str | None:
    try:
        import pyttsx3  # type: ignore
    except Exception:
        return None
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        engine.stop()
    except Exception:
        return None
    if os.path.isfile(out_path) and os.path.getsize(out_path) > 44:
        return "pyttsx3"
    return None


def _try_windows_sapi(text: str, out_path: str) -> str | None:
    if os.name != "nt":
        return None
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return None
    safe_text = text.replace("'", "''")
    safe_out = str(out_path).replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        f"$s.SetOutputToWaveFile('{safe_out}');"
        f"$s.Speak('{safe_text}');"
        "$s.Dispose()"
    )
    try:
        res = subprocess.run(
            [ps, "-NoProfile", "-Command", script],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=90,
        )
    except Exception:
        return None
    if res.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 44:
        return "windows-sapi"
    return None


def _synthesize_voice(text: str, out_path: str, prefer_engine: str | None = None) -> str | None:
    """Tenta sintetizar voz local; devolve o nome do motor usado ou None."""
    if not text or not text.strip():
        return None
    candidates: list[tuple[str, Any]] = [
        ("pyttsx3", _try_pyttsx3),
        ("windows-sapi", _try_windows_sapi),
    ]
    for name, fn in candidates:
        if prefer_engine is not None and name != prefer_engine:
            continue
        engine = fn(text, out_path)
        if engine:
            return engine
    return None


def _mix_voice_over_bed(ffmpeg: str, bed_path: str, voice_path: str, output_path: str,
                        duration: float, sample_rate: int, channels: int) -> None:
    layout = _channel_layout(channels)
    bed_chain = f"[0:a]volume=0.55,aformat=channel_layouts={layout}:sample_rates={sample_rate}[bed]"
    voice_chain = f"[1:a]volume=1.7,apad,aformat=channel_layouts={layout}:sample_rates={sample_rate}[voice]"
    mix_tail = "[bed][voice]amix=inputs=2:duration=first:dropout_transition=0"
    if duration >= _MIN_LOUDNORM_DURATION:
        mix_tail += f",loudnorm=I={DEFAULT_LOUDNESS_LUFS}:TP=-2.0:LRA=11"
    mix_tail += f",aformat=sample_fmts=s16:channel_layouts={layout}:sample_rates={sample_rate}[out]"
    filter_complex = ";".join([bed_chain, voice_chain, mix_tail])
    cmd = [
        ffmpeg, "-y", "-i", bed_path, "-i", voice_path,
        "-filter_complex", filter_complex, "-map", "[out]",
        "-t", f"{duration:.3f}", "-c:a", "pcm_s16le", output_path,
    ]
    _run(cmd)


def _default_narration(brand_kit: dict) -> str:
    name = str(brand_kit.get("brandName") or "").strip()
    tagline = str(brand_kit.get("tagline") or "").strip()
    if name and tagline:
        return f"{name}. {tagline}."
    return (name or tagline or "Multitrack Hub") + "."


# ---------------------------------------------------------------------------
# Ponto de entrada programatico
# ---------------------------------------------------------------------------
def generate_audio(tenant_id: str, output_path: str, duration: float = DEFAULT_DURATION,
                   mode: str = AMBIENT_BED, root: str = ".",
                   text: str | None = None, sample_rate: int = DEFAULT_SAMPLE_RATE,
                   channels: int = DEFAULT_CHANNELS, prefer_engine: str | None = None) -> dict:
    """Gera a trilha `.wav` sincronizada e devolve metadados de inspecao."""
    root_real = os.path.realpath(root)
    render_local.ensure_video_tools(root_real)
    ffmpeg = build_video.get_ffmpeg()

    # 1. Trava de seguranca: carrega/valida o tenant e exige allowAudioTrack=true.
    ctx = tenant_validator.load_and_validate_tenant(tenant_id, root=root_real, strict=True)
    audio_policy = ctx["guardrails"].get("audioPolicy", {})
    allow_audio = bool(audio_policy.get("allowAudioTrack", False))
    if not allow_audio:
        raise AudioTtsError(
            "AUDIO_NAO_PERMITIDO",
            f"tenant '{tenant_id}' tem allowAudioTrack=false; geracao de audio recusada",
        )

    # 2. Valida modo e parametros numericos.
    if mode not in SUPPORTED_MODES:
        raise AudioTtsError("MODO_INVALIDO", f"modo '{mode}' (suportados: {SUPPORTED_MODES})")
    dur = float(duration)
    if dur <= 0:
        raise AudioTtsError("DURACAO_INVALIDA", f"duration={duration} deve ser > 0")
    if int(sample_rate) <= 0:
        raise AudioTtsError("SAMPLE_RATE_INVALIDO", f"sample_rate={sample_rate} deve ser > 0")
    if int(channels) not in (1, 2):
        raise AudioTtsError("CANAIS_INVALIDOS", f"channels={channels} (use 1 ou 2)")

    # 3. Valida o caminho de saida (contido na raiz) antes de qualquer escrita.
    output_abs = _resolve_output(root_real, output_path)
    if not render_local.contained(root_real, output_abs):
        raise AudioTtsError("OUTPUT_FORA_DA_RAIZ", "output esta fora da raiz do projeto")
    os.makedirs(os.path.dirname(output_abs), exist_ok=True)

    # 4. Gera a cama sonora e, quando aplicavel, a voz sobre ela.
    used_mode = AMBIENT_BED
    tts_engine: str | None = None
    staging_dir = os.path.join(root_real, ".workspace", "tmp", "audio-tts")
    os.makedirs(staging_dir, exist_ok=True)
    token = f"{tenant_id}-{os.getpid()}"
    bed_tmp = os.path.join(staging_dir, f"bed-{token}.wav")
    voice_tmp = os.path.join(staging_dir, f"voice-{token}.wav")

    try:
        _synthesize_ambient_bed(ffmpeg, bed_tmp, dur, int(sample_rate), int(channels))

        if mode == NARRATION_BED:
            narration_text = (text or "").strip() or _default_narration(ctx["brandKit"])
            violations = tenant_validator.validate_text_against_guardrails(
                narration_text, ctx["guardrails"], check_ui_elements=True,
                ignore_editorial_footer=True,
            )
            if violations:
                raise AudioTtsError("GUARDRAIL_VIOLACAO", "; ".join(violations))
            engine = _synthesize_voice(narration_text, voice_tmp, prefer_engine=prefer_engine)
            if engine:
                _mix_voice_over_bed(
                    ffmpeg, bed_tmp, voice_tmp, output_abs, dur,
                    int(sample_rate), int(channels),
                )
                used_mode = NARRATION_BED
                tts_engine = engine
            else:
                # Fallback seguro: entrega a cama sonora pura.
                shutil.copyfile(bed_tmp, output_abs)
                used_mode = AMBIENT_BED
                tts_engine = "fallback-ambient-bed"
        else:
            shutil.copyfile(bed_tmp, output_abs)
    finally:
        for tmp in (bed_tmp, voice_tmp):
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except OSError:
                pass

    # 5. Inspecao real + metadados.
    info = build_video.probe_media(output_abs)
    astream = next(
        (s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {}
    )
    measured_duration = float(info.get("format", {}).get("duration", 0.0))

    return {
        "schemaVersion": 1,
        "tenantId": tenant_id,
        "mode": used_mode,
        "requestedMode": mode,
        "ttsEngine": tts_engine,
        "path": render_local.rel(root_real, output_abs),
        "sha256": render_local.sha256_file(output_abs),
        "bytes": os.path.getsize(output_abs),
        "duration": measured_duration,
        "sampleRate": int(astream.get("sample_rate", sample_rate)),
        "channels": int(astream.get("channels", channels)),
        "codec": astream.get("codec_name"),
        "loudnessTargetLufs": DEFAULT_LOUDNESS_LUFS if dur >= _MIN_LOUDNORM_DURATION else None,
        "allowAudioTrack": allow_audio,
        "guardrails": {
            "allowAudioTrack": allow_audio,
            "requireSrt": bool(audio_policy.get("requireSrt")),
            "requireExternalNarration": bool(audio_policy.get("requireExternalNarration")),
        },
        "command": (
            f"python tools/audio_tts.py --tenant {tenant_id} "
            f"--output {render_local.rel(root_real, output_abs)} "
            f"--duration {dur:.3f} --mode {mode}"
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gerador modular de trilhas de audio para Shorts (Agente 2 - Etapa 3)"
    )
    parser.add_argument("--tenant", required=True, help="Slug do tenant (ex.: multitrack-hub)")
    parser.add_argument("--output", required=True, help="Caminho do .wav de saida")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="Duracao em segundos")
    parser.add_argument("--mode", choices=list(SUPPORTED_MODES), default=AMBIENT_BED)
    parser.add_argument("--text", default=None, help="Texto de narracao (modo narration-bed)")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS, choices=[1, 2])
    parser.add_argument("--engine", default=None, choices=["pyttsx3", "windows-sapi"])
    parser.add_argument("--root", default=os.getcwd(), help="Raiz do checkout")
    parser.add_argument("--json", action="store_true", help="Emite metadados JSON no stdout")
    args = parser.parse_args(argv)

    try:
        result = generate_audio(
            args.tenant, args.output, duration=args.duration, mode=args.mode,
            root=args.root, text=args.text, sample_rate=args.sample_rate,
            channels=args.channels, prefer_engine=args.engine,
        )
    except tenant_validator.TenantContractError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    except AudioTtsError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except build_video.DeliveryError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Audio gerado: {result['path']} "
            f"({result['mode']}, {result['duration']:.3f}s, "
            f"{result['sampleRate']} Hz, {result['channels']} ch, codec {result['codec']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())