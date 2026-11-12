"""
Video Builder Orchestrator for Marca Salão Marketing (R002: exportacao transacional sem audio).
Combines background footage/images, motion overlays and styled subtitles via FFmpeg.
Follows video-use hard rules:
- Proper PTS alignment for overlays
- Subtitles applied LAST in the filter chain
Politica do projeto (AGENTS.md / WORKFLOW.md): video sem nenhuma faixa de audio.
Nunca injeta audio silencioso; entrada de audio e recusada pela politica vigente.
"""

import os
import json
import argparse
import subprocess
import shutil


class DeliveryError(Exception):
    """Falha de validacao ou renderizacao; mensagem sanitizada, sem stack trace."""


def get_ffmpeg():
    cmd = shutil.which("ffmpeg")
    if not cmd:
        raise DeliveryError("ffmpeg nao encontrado no PATH; instale ou exponha o binario antes de exportar")
    return cmd


def get_ffprobe():
    cmd = shutil.which("ffprobe")
    if not cmd:
        raise DeliveryError("ffprobe nao encontrado no PATH; instale ou exponha o binario antes de inspecionar")
    return cmd

def run_cmd(cmd_list):
    print("Executing:", " ".join(cmd_list))
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg Error:\n", res.stderr)
        return False
    return True

def build_video(bg_path, audio_path=None, overlay_path=None, subtitles_path=None,
                output_path="final.mp4", duration=8.0, resolution="1080x1920", fps=30,
                preset="medium", overlay_start=0.0, overlay_end=None,
                overlay_fade_in=0.0, overlay_fade_out=0.0, subtitle_style=None):
    if audio_path:
        raise DeliveryError(
            "Entrada de audio recusada: a politica do projeto entrega video sem faixa de audio"
        )
    ffmpeg = get_ffmpeg()
    w, h = resolution.split("x")
    if overlay_end is None:
        overlay_end = duration

    # Check if background is image or video
    ext = os.path.splitext(bg_path)[1].lower()
    is_image = ext in [".png", ".jpg", ".jpeg", ".webp"]

    inputs = []
    filter_complex = []

    # Input 0: Background
    if is_image:
        inputs.extend(["-loop", "1", "-t", str(duration), "-i", bg_path])
    else:
        inputs.extend(["-i", bg_path])

    filter_complex.append(f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[base]")
    last_v = "[base]"

    # Input 1: Overlay if present
    curr_input_idx = 1
    if overlay_path and os.path.exists(overlay_path):
        inputs.extend(["-loop", "1", "-t", str(duration), "-i", overlay_path])
        fades = []
        if overlay_fade_in > 0:
            fades.append(f"fade=t=in:st={overlay_start}:d={overlay_fade_in}:alpha=1")
        if overlay_fade_out > 0:
            fades.append(f"fade=t=out:st={overlay_end - overlay_fade_out}:d={overlay_fade_out}:alpha=1")
        chain = f"[{curr_input_idx}:v]setpts=PTS-STARTPTS"
        if fades:
            chain += "," + ",".join(fades)
        filter_complex.append(chain + "[ovl]")
        filter_complex.append(f"{last_v}[ovl]overlay=0:0:enable='between(t,{overlay_start},{overlay_end})'[overlaid]")
        last_v = "[overlaid]"
        curr_input_idx += 1

    # Subtitles (applied LAST in filter chain)
    if subtitles_path and os.path.exists(subtitles_path):
        # Escape path for FFmpeg subtitles filter
        clean_sub = subtitles_path.replace("\\", "/").replace(":", "\\:")
        # Reel style: bold, yellow/white text, shadow, centered at bottom
        sub_style = subtitle_style or "Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=60"
        filter_complex.append(f"{last_v}subtitles='{clean_sub}':force_style='{sub_style}'[vfinal]")
        last_v = "[vfinal]"

    # Politica sem audio: nenhuma entrada de audio, nenhum anullsrc, nenhum mux de faixa.
    cmd = [ffmpeg, "-y"] + inputs + ["-filter_complex", ";".join(filter_complex), "-map", last_v]
    cmd.extend(["-an", "-c:v", "libx264", "-preset", preset, "-pix_fmt", "yuv420p", "-t", str(duration), output_path])

    success = run_cmd(cmd)
    if success:
        print(f"\nVideo rendered successfully: {output_path}")
    return success

def probe_media(path):
    """Inspecao real via ffprobe; devolve dict com streams/format ou lanca DeliveryError."""
    ffprobe = get_ffprobe()
    res = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise DeliveryError(f"ffprobe falhou ao inspecionar o artefato: {os.path.basename(str(path))}")
    return json.loads(res.stdout)


def validate_mp4(path, width, height, fps, duration, duration_tolerance=0.2):
    """Exige 1 stream de video, 0 de audio, geometria/fps/duracao/pix_fmt esperados."""
    info = probe_media(path)
    streams = info.get("streams", [])
    video = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    problems = []
    measured_fps = None
    if len(video) != 1:
        problems.append(f"streams de video: {len(video)} (esperado 1)")
    if audio:
        problems.append(f"streams de audio: {len(audio)} (esperado 0)")
    if video:
        v = video[0]
        if v.get("codec_name") != "h264":
            problems.append(f"codec: {v.get('codec_name')} (esperado h264)")
        if int(v.get("width", 0)) != width or int(v.get("height", 0)) != height:
            problems.append(f"dimensoes: {v.get('width')}x{v.get('height')} (esperado {width}x{height})")
        if v.get("pix_fmt") != "yuv420p":
            problems.append(f"pix_fmt: {v.get('pix_fmt')} (esperado yuv420p)")
        rate = v.get("avg_frame_rate", "0/1")
        num, _, den = rate.partition("/")
        measured_fps = float(num) / float(den or 1)
        if abs(measured_fps - fps) > 0.01:
            problems.append(f"fps: {measured_fps} (esperado {fps})")
    measured_duration = float(info.get("format", {}).get("duration", 0))
    if abs(measured_duration - duration) > duration_tolerance:
        problems.append(f"duracao: {measured_duration:.3f}s (esperado {duration:.3f}s)")
    if problems:
        raise DeliveryError("MP4 reprovado na inspecao: " + "; ".join(problems))
    return {
        "videoStreams": len(video),
        "audioStreams": len(audio),
        "codec": video[0].get("codec_name") if video else None,
        "width": int(video[0].get("width", 0)) if video else None,
        "height": int(video[0].get("height", 0)) if video else None,
        "fps": measured_fps,
        "pixFmt": video[0].get("pix_fmt") if video else None,
        "duration": measured_duration,
    }


def transactional_export(staging_dir, artifacts, render, validators):
    """Gera em staging, valida tudo e so entao promove com substituicao atomica.

    artifacts: dict nome -> {"staging": nome do arquivo, "dest": caminho final}
    render: callable(staging_paths) que produz os artefatos em staging
    validators: callable(staging_paths) que lanca DeliveryError em qualquer falha
    Em falha, nenhum destino e tocado e o staging permanece para diagnostico.
    """
    staging_dir = os.path.abspath(staging_dir)
    os.makedirs(staging_dir, exist_ok=True)
    staging_paths = {name: os.path.join(staging_dir, spec["staging"])
                     for name, spec in artifacts.items()}
    render(staging_paths)
    validators(staging_paths)
    for name, spec in artifacts.items():
        dest = os.path.abspath(spec["dest"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.replace(staging_paths[name], dest)
    return staging_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Marca Salão Video Orchestrator (sem audio)")
    parser.add_argument("--bg", required=True, help="Background image or video file")
    parser.add_argument("--audio", help="Recusado pela politica sem audio do projeto")
    parser.add_argument("--overlay", help="Transparent PNG/WebM animation overlay (optional)")
    parser.add_argument("--subtitles", help="Subtitles SRT file (optional)")
    parser.add_argument("--duration", type=float, default=8.0, help="Duration in seconds")
    parser.add_argument("--resolution", default="1080x1920", help="Resolution e.g. 1080x1920 or 1920x1080")
    parser.add_argument("--preset", default="medium", help="libx264 preset")
    parser.add_argument("-o", "--output", default="final.mp4", help="Output file path")

    args = parser.parse_args()
    try:
        ok = build_video(args.bg, args.audio, args.overlay, args.subtitles, args.output,
                         args.duration, args.resolution, preset=args.preset)
    except DeliveryError as exc:
        print(f"Erro: {exc}")
        raise SystemExit(1)
    raise SystemExit(0 if ok else 1)
