"""
Script to Subtitles (.srt / .ass) Generator for Marca Salão Marketing.
Generates styled subtitles without needing external APIs or heavy AI models.
"""

import sys
import os
import re

def seconds_to_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_srt_from_script(script_path: str, output_srt: str, default_duration_per_line: float = 3.5):
    """
    Parses a text script file.
    Supports formats:
      1) Timestamped lines: [00:00 - 00:03] Texto da fala
      2) Second-based lines: 0 - 3.5 | Texto da fala
      3) Plain lines: Texto linha a linha (usa default_duration_per_line)
    """
    if not os.path.exists(script_path):
        print(f"Error: Script file not found: {script_path}")
        return False

    with open(script_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip() and not l.strip().startswith("#")]

    srt_entries = []
    current_time = 0.0

    for i, line in enumerate(lines, start=1):
        # Match [00:01 - 00:04] Text
        m_time = re.match(r"^\[?(\d{1,2}:?\d{2}(?:\.\d+)?)\s*[-–—]\s*(\d{1,2}:?\d{2}(?:\.\d+)?)\]?\s*[:|]?\s*(.+)$", line)
        # Match 0.0 - 3.5 | Text
        m_sec = re.match(r"^(\d+(?:\.\d+)?)\s*[-–—]\s*(\d+(?:\.\d+)?)\s*[:|]\s*(.+)$", line)

        if m_time:
            # Parse MM:SS or HH:MM:SS
            def parse_ts(ts):
                parts = [float(p) for p in ts.split(":")]
                if len(parts) == 2:
                    return parts[0] * 60 + parts[1]
                elif len(parts) == 3:
                    return parts[0] * 3600 + parts[1] * 60 + parts[2]
                return float(ts)
            start_sec = parse_ts(m_time.group(1))
            end_sec = parse_ts(m_time.group(2))
            text = m_time.group(3).strip()
            current_time = end_sec
        elif m_sec:
            start_sec = float(m_sec.group(1))
            end_sec = float(m_sec.group(2))
            text = m_sec.group(3).strip()
            current_time = end_sec
        else:
            start_sec = current_time
            end_sec = current_time + default_duration_per_line
            text = line
            current_time = end_sec

        srt_entries.append((i, start_sec, end_sec, text))

    with open(output_srt, "w", encoding="utf-8") as f:
        for idx, start, end, txt in srt_entries:
            f.write(f"{idx}\n")
            f.write(f"{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}\n")
            # Upper-case chunks or high-impact text
            f.write(f"{txt}\n\n")

    print(f"Subtitles written successfully: {output_srt} ({len(srt_entries)} entries)")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script_to_subtitles.py <input_script.txt> <output.srt> [duration_per_line]")
        sys.exit(1)
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else 3.5
    generate_srt_from_script(sys.argv[1], sys.argv[2], dur)
