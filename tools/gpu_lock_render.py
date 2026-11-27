"""Run a Remotion command under a machine-wide render lock, so only one render uses the GPU / CPU at a time.

Usage (from anywhere; --cwd is the Remotion project):
  python -X utf8 tools/gpu_lock_render.py --cwd . -- still Full out/x.png --frame=72 --scale=1.5
  python -X utf8 tools/gpu_lock_render.py --cwd . -- render Full out/full.mp4 --scale=1.5 --codec=h264 --crf=16
Remotion uses its own headless Chrome by default; set PVP_BROWSER=<path to chrome> to use an installed browser.
The lock and the render log live in the system temp folder (pvp_render.lock / pvp_render.log).
"""
import argparse
import datetime as dt
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

LOCK_FILE = Path(tempfile.gettempdir()) / "pvp_render.lock"
LOG_FILE = Path(tempfile.gettempdir()) / "pvp_render.log"

if os.name == "nt":
    import msvcrt

    def try_lock(fp):
        fp.seek(0); msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)

    def unlock(fp):
        fp.seek(0); msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def try_lock(fp):
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def unlock(fp):
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


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
    cmd = ["npx.cmd" if os.name == "nt" else "npx", "remotion"] + rem
    browser = os.environ.get("PVP_BROWSER")
    if browser and not any(a.startswith("--browser-executable") for a in rem):
        cmd.append(f"--browser-executable={browser}")
    if not any(a.startswith("--log") for a in rem):
        cmd.append("--log=error")

    t_wait = time.time()
    fp = open(LOCK_FILE, "a+b")
    acquired = False
    while time.time() - t_wait < args.wait_timeout:
        try:
            try_lock(fp)
            acquired = True
            break
        except OSError:
            time.sleep(2.5)

    if not acquired:
        fp.close()
        log_line(f"TIMEOUT waiting for render lock: cwd={cwd} cmd={' '.join(rem)}")
        print("Timed out waiting for the render lock", file=sys.stderr)
        return 124

    try:
        wait_s = round(time.time() - t_wait, 1)
        log_line(f"START (waited {wait_s}s) pid={os.getpid()} cwd={cwd} :: {' '.join(rem)}")
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=str(cwd), shell=False)
        dur_s = round(time.time() - t0, 1)
        log_line(f"DONE rc={proc.returncode} dur={dur_s}s cwd={cwd} :: {' '.join(rem)}")
        return proc.returncode
    finally:
        try:
            unlock(fp)
        except OSError:
            pass
        fp.close()


if __name__ == "__main__":
    sys.exit(main())
