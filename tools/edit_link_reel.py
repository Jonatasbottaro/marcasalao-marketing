"""
Automated Reel Editor for 'Prof Enviado Link.mp4'.
Cuts 4 dynamic scenes, applies premium blurred background padding for 1080x1920,
layers HyperFrames animated overlays and burns synced subtitles.
"""

import os
import sys
import subprocess
import shutil

FFMPEG = shutil.which("ffmpeg") or r"C:\Users\Administrador\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"

def run_cmd(cmd):
    print("Executing:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Error:\n", res.stderr)
        return False
    return True

def edit_reel():
    raw_video = "videos_brutos/Prof Enviado Link.mp4"
    overlay_html_dir = "templates/reel_link_overlay"
    overlay_webm = "templates/reel_link_overlay/overlay.webm"
    subtitles = "04-legendas/roteiro_enviar_link.srt"
    output_dir = "02-reels-shorts"
    final_output = os.path.join(output_dir, "Reel_Enviar_Link_Final.mp4")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("scratch", exist_ok=True)

    # Step 1: Render HyperFrames overlay (transparent WebM) if not present
    if not os.path.exists(overlay_webm):
        print("\n--- Step 1: Rendering HyperFrames Overlay (27s Transparent WebM) ---")
        render_cmd = ["npx", "hyperframes", "render", "--format", "webm", overlay_html_dir, "-o", overlay_webm]
        subprocess.run(render_cmd, shell=True, check=True)
    else:
        print("\n--- Step 1: Reusing already rendered transparent overlay.webm ---")

    # Step 2: Cut the 4 segments and format them into 1080x1920 with blurred background
    segments = [
        ("0.0", "3.0", "scratch/seg1.mp4"),
        ("34.0", "8.0", "scratch/seg2.mp4"),
        ("68.0", "6.0", "scratch/seg3.mp4"),
        ("75.0", "10.0", "scratch/seg4.mp4"),
    ]

    print("\n--- Step 2: Cutting & Styling Segments ---")
    concat_list = "scratch/concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for i, (ss, dur, out_seg) in enumerate(segments, start=1):
            vf = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[blurred];"
                "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[crisp];"
                "[blurred][crisp]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30"
            )
            cmd = [
                FFMPEG, "-y", "-ss", ss, "-t", dur, "-i", raw_video,
                "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-an", out_seg
            ]
            run_cmd(cmd)
            f.write(f"file '{os.path.abspath(out_seg).replace('\\', '/')}'\n")

    # Step 3: Concat segments
    print("\n--- Step 3: Concatenating Cut Segments ---")
    concat_video = "scratch/concatenated_base.mp4"
    concat_cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", concat_video
    ]
    run_cmd(concat_cmd)

    # Step 4: Final composite with Transparent HyperFrames Overlay + Subtitles
    print("\n--- Step 4: Final Compositing with Overlays & Subtitles ---")
    clean_sub = subtitles.replace("\\", "/").replace(":", "\\:")
    # Subtitle style: clean, bottom centered with subtle dark backdrop, font size 13
    sub_style = "Fontname=Arial,Fontsize=13,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=120"

    filter_complex = (
        f"[0:v][1:v]overlay=0:0:enable='between(t,0,27)'[overlaid];"
        f"[overlaid]subtitles='{clean_sub}':force_style='{sub_style}'[vfinal]"
    )

    final_cmd = [
        FFMPEG, "-y",
        "-i", concat_video,
        "-c:v", "libvpx-vp9", "-i", overlay_webm,
        "-f", "lavfi", "-t", "27.0", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        "-t", "27.0",
        final_output
    ]
    success = run_cmd(final_cmd)

    if success:
        print(f"\n==============================================")
        print(f" Reel Finalizado com Sucesso: {final_output}")
        print(f"==============================================")
    return success

if __name__ == "__main__":
    edit_reel()
