"""Deterministic video QA audit for Remotion renders (black / freeze / loudness / contact sheet).

Checks resolution, FPS, duration, codec, audio stream, blackdetect, freezedetect,
ebur128 integrated loudness / true peak, and optionally writes a 32-tile contact sheet.

Usage:
  python -X utf8 qa_video_audit.py --input <mp4> [--json <out.json>] [--sheet <out.jpg>]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def run_ffprobe(mp4: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(mp4)
    ]
    out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")
    return json.loads(out)


def detect_video_anomalies(mp4: Path, has_audio: bool = True) -> dict:
    cmd = [
        "ffmpeg", "-nostdin", "-i", str(mp4),
        "-vf", "blackdetect=d=0.25:pix_th=0.05,freezedetect=n=-60dB:d=4.0",
    ]
    if has_audio:
        cmd.extend(["-af", "ebur128=peak=true"])
    cmd.extend(["-f", "null", "-"])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = proc.stderr
    blacks = []
    for m in re.finditer(r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)", log):
        blacks.append({"start": float(m.group(1)), "end": float(m.group(2)), "dur": float(m.group(3))})
    freezes = []
    for m in re.finditer(r"freeze_start:\s*([\d.]+).*?freeze_duration:\s*([\d.]+)", log, re.S):
        freezes.append({"start": float(m.group(1)), "dur": float(m.group(2))})
    lufs_m = re.findall(r"I:\s*([-\d.]+)\s*LUFS", log)
    tp_m = re.findall(r"Peak:\s*([-\d.]+)\s*dBFS", log)
    return {
        "black_segments": blacks,
        "freeze_segments": freezes,
        "integrated_lufs": float(lufs_m[-1]) if lufs_m else None,
        "true_peak_dbfs": float(tp_m[-1]) if tp_m else None,
        "ffmpeg_rc": proc.returncode,
    }


def make_sheet(mp4: Path, out_jpg: Path, dur: float, n: int = 32, cols: int = 4, w: int = 480) -> None:
    step = max(1.0, dur / n)
    raw = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(mp4),
         "-vf", f"fps=1/{step:.3f},scale={w}:-1", "-frames:v", str(n),
         "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, check=True
    ).stdout
    ims, i = [], 0
    while True:
        j = raw.find(b"\x89PNG", i + 1)
        ims.append(Image.open(__import__("io").BytesIO(raw[i: j if j > 0 else None])).convert("RGB"))
        if j < 0:
            break
        i = j
    if not ims:
        return
    h = ims[0].height
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + 20)), (12, 16, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    for k, im in enumerate(ims):
        x, y = (k % cols) * w, (k // cols) * (h + 20)
        t = k * step
        draw.text((x + 6, y + 3), f"{int(t // 60)}:{t % 60:04.1f}", fill=(120, 210, 240), font=font)
        sheet.paste(im, (x, y + 20))
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_jpg, quality=86)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--json")
    ap.add_argument("--sheet")
    ap.add_argument("--allow-silent", action="store_true", help="Allow silent clips (e.g. muted 12s web hero loops)")
    args = ap.parse_args()
    mp4 = Path(args.input).resolve()
    if not mp4.exists():
        print(json.dumps({"status": "FAIL", "error": f"Missing file: {mp4}"}))
        return 1

    probe = run_ffprobe(mp4)
    streams = probe.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = float(probe.get("format", {}).get("duration", 0))
    anom = detect_video_anomalies(mp4, has_audio=bool(a_stream))

    bookend_blacks = [
        b for b in anom["black_segments"]
        if (b["start"] < 0.6 or b["end"] > dur - 0.6) and b["dur"] <= 0.6
    ]
    mid_blacks = [b for b in anom["black_segments"] if b not in bookend_blacks]
    anom["bookend_black_segments"] = bookend_blacks
    anom["black_segments"] = mid_blacks

    issues = []
    if not v_stream:
        issues.append("missing video stream")
    if not a_stream and not args.allow_silent:
        issues.append("missing audio stream")
    if a_stream and args.allow_silent:
        issues.append("unexpected audio stream in silent loop")
    if anom["ffmpeg_rc"] != 0:
        issues.append(f"ffmpeg anomaly scan failed (rc={anom['ffmpeg_rc']})")
    if mid_blacks:
        issues.append(f"{len(mid_blacks)} black segment(s)")
    if anom["freeze_segments"]:
        issues.append(f"{len(anom['freeze_segments'])} freeze segment(s)")
    if dur < 10:
        issues.append(f"short duration {dur:.2f}s")

    fps_str = v_stream.get("r_frame_rate", "0/1") if v_stream else "0/1"
    num, den = (int(x) for x in fps_str.split("/")) if "/" in fps_str else (0, 1)
    fps = round(num / max(1, den), 2)

    report = {
        "file": str(mp4),
        "size_mb": round(mp4.stat().st_size / 1048576, 2),
        "duration_s": round(dur, 2),
        "width": v_stream.get("width") if v_stream else None,
        "height": v_stream.get("height") if v_stream else None,
        "fps": fps,
        "vcodec": v_stream.get("codec_name") if v_stream else None,
        "acodec": a_stream.get("codec_name") if a_stream else None,
        "sample_rate": int(a_stream.get("sample_rate", 0)) if a_stream else None,
        **anom,
        "issues": issues,
        "status": "PASS" if not issues else "WARN",
    }
    if args.sheet and v_stream:
        make_sheet(mp4, Path(args.sheet).resolve(), dur)
        report["sheet"] = str(Path(args.sheet).resolve())
    if args.json:
        jp = Path(args.json).resolve()
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
