"""
Video Builder Orchestrator for Marca Salão Marketing.
Combines background footage/images, HyperFrames motion graphics, audio, and styled subtitles via FFmpeg.
Follows video-use hard rules:
- 30ms audio fade at cut points
- Proper PTS alignment for overlays
- Subtitles applied LAST in the filter chain
"""

import os
import sys
import argparse
import subprocess
import shutil

def get_ffmpeg():
    cmd = shutil.which("ffmpeg")
    if not cmd:
        cmd = r"C:\Users\Administrador\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
    return cmd

def run_cmd(cmd_list):
    print("Executing:", " ".join(cmd_list))
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg Error:\n", res.stderr)
        return False
    return True

def build_video(bg_path, audio_path=None, overlay_path=None, subtitles_path=None, output_path="final.mp4", duration=8.0, resolution="1080x1920", fps=30):
    ffmpeg = get_ffmpeg()
    w, h = resolution.split("x")

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
        inputs.extend(["-i", overlay_path])
        filter_complex.append(f"[{curr_input_idx}:v]setpts=PTS-STARTPTS[ovl]")
        filter_complex.append(f"{last_v}[ovl]overlay=0:0:enable='between(t,0,{duration})'[overlaid]")
        last_v = "[overlaid]"
        curr_input_idx += 1

    # Subtitles (applied LAST in filter chain)
    if subtitles_path and os.path.exists(subtitles_path):
        # Escape path for FFmpeg subtitles filter
        clean_sub = subtitles_path.replace("\\", "/").replace(":", "\\:")
        # Reel style: bold, yellow/white text, shadow, centered at bottom
        sub_style = "Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=60"
        filter_complex.append(f"{last_v}subtitles='{clean_sub}':force_style='{sub_style}'[vfinal]")
        last_v = "[vfinal]"

    # Audio input
    audio_inputs = []
    audio_maps = []
    if audio_path and os.path.exists(audio_path):
        audio_inputs.extend(["-i", audio_path])
        audio_maps.extend(["-map", f"{curr_input_idx}:a", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=in:st=0:d=0.03,afade=t=out:st={duration-0.03}:d=0.03"])
    else:
        # Generate silent audio track for container compatibility
        audio_inputs.extend(["-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])
        audio_maps.extend(["-map", f"{curr_input_idx}:a", "-c:a", "aac"])

    cmd = [ffmpeg, "-y"] + inputs + audio_inputs + ["-filter_complex", ";".join(filter_complex), "-map", last_v] + audio_maps
    cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration), output_path])

    success = run_cmd(cmd)
    if success:
        print(f"\nVideo rendered successfully: {output_path}")
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Marca Salão Video Orchestrator")
    parser.add_argument("--bg", required=True, help="Background image or video file")
    parser.add_argument("--audio", help="Audio voiceover file (optional)")
    parser.add_argument("--overlay", help="HyperFrames MP4/WebM animation overlay (optional)")
    parser.add_argument("--subtitles", help="Subtitles SRT file (optional)")
    parser.add_argument("--duration", type=float, default=8.0, help="Duration in seconds")
    parser.add_argument("--resolution", default="1080x1920", help="Resolution e.g. 1080x1920 or 1920x1080")
    parser.add_argument("-o", "--output", default="final.mp4", help="Output file path")

    args = parser.parse_args()
    build_video(args.bg, args.audio, args.overlay, args.subtitles, args.output, args.duration, args.resolution)
