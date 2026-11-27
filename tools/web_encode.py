"""Encode the CRF-16 master into a web / e-mail attachment version under a size cap (default 95 MB).

Two-pass-free: picks the video bitrate from the duration so (video + 160 kb/s AAC) lands under the cap, with a 3 %
margin, x264 preset slow, High profile, yuv420p, +faststart (plays while downloading).
usage: python -X utf8 tools/web_encode.py master.mp4 web.mp4 [cap_MB]
"""
import subprocess, sys
from pathlib import Path

src, dst = sys.argv[1], sys.argv[2]
cap_mb = float(sys.argv[3]) if len(sys.argv) > 3 else 95.0
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
audio_k = 160
video_k = int((cap_mb * 0.97 * 8 * 1000 * 1000 / dur) / 1000) - audio_k
video_k = max(800, min(video_k, 4000))
print(f"duration {dur:.1f}s -> video {video_k} kb/s")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:v", "libx264", "-preset", "slow", "-b:v", f"{video_k}k",
                "-maxrate", f"{int(video_k * 1.4)}k", "-bufsize", f"{video_k * 3}k", "-pix_fmt", "yuv420p", "-profile:v", "high",
                "-c:a", "aac", "-b:a", f"{audio_k}k", "-movflags", "+faststart", dst], check=True)
size = Path(dst).stat().st_size / 1e6
print(f"{dst}: {size:.1f} MB")
if size > cap_mb: raise SystemExit(f"over the {cap_mb} MB cap")
