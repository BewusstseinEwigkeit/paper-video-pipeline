"""Single-Flight GPU Lock wrapper for all Remotion renders across the overnight arena.

Usage:
  python -X utf8 gpu_lock_render.py --cwd <track_dir> -- still BtwFull out\\check\\x.png --frame=72 --scale=1.5
  python -X utf8 gpu_lock_render.py --cwd <track_dir> -- render BtwFull out\\full.mp4 --codec=h264 --crf=16
"""
import argparse
import datetime as dt
import msvcrt
import os
import subprocess
import sys
import time
from pathlib import Path

ARENA = Path(__file__).resolve().parent
LOCK_FILE = ARENA / "_gpu.lock"
LOG_FILE = ARENA / "render_queue.log"
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def log_line(msg: str) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as fp:
        fp.write(f"[{ts}] {msg}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--wait-timeout", type=int, default=5400)
    args, rem = parser.parse_known_args()
    if rem and rem[0] == "--":
        rem = rem[1:]
    if not rem:
        print("Error: missing remotion subcommand args after --", file=sys.stderr)
        return 2

    cwd = Path(args.cwd).resolve()
    cmd = ["npx.cmd", "remotion"] + rem
    if not any(a.startswith("--browser-executable") for a in rem):
        cmd.append(f"--browser-executable={CHROME_EXE}")
    if not any(a.startswith("--log") for a in rem):
        cmd.append("--log=error")

    ARENA.mkdir(parents=True, exist_ok=True)
    t_wait = time.time()
    fp = open(LOCK_FILE, "a+b")
    acquired = False
    while time.time() - t_wait < args.wait_timeout:
        try:
            fp.seek(0)
            msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
            acquired = True
            break
        except OSError:
            time.sleep(2.5)

    if not acquired:
        fp.close()
        log_line(f"TIMEOUT waiting for GPU lock: cwd={cwd.name} cmd={' '.join(rem)}")
        print("Timed out waiting for GPU lock", file=sys.stderr)
        return 124

    try:
        wait_s = round(time.time() - t_wait, 1)
        log_line(f"START (waited {wait_s}s) pid={os.getpid()} cwd={cwd.name} :: {' '.join(rem)}")
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=str(cwd), shell=False)
        dur_s = round(time.time() - t0, 1)
        log_line(f"DONE rc={proc.returncode} dur={dur_s}s cwd={cwd.name} :: {' '.join(rem)}")
        return proc.returncode
    finally:
        try:
            fp.seek(0)
            msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        fp.close()


if __name__ == "__main__":
    sys.exit(main())
