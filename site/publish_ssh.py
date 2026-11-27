"""Push site files to a static host over SSH (tar stream) and verify them through the public URL.

A typical host is nginx + a cloudflared quick tunnel on a small VM; this script is the generic "sync + verify" step.
  * files are streamed as one tar over ssh (no scp per file, no rsync dependency on Windows);
  * video files must be listed explicitly - a page-only sync leaves the old video in place;
  * verification fetches the page and asks every .mp4 for its first and last byte range: 206 + the local size means
    the file is complete and seekable.
usage: python -X utf8 site/publish_ssh.py <ssh-host-alias> <remote-dir> <local-site-dir> <public-url> file [file ...]
example (PowerShell, or Git Bash with MSYS_NO_PATHCONV=1): python -X utf8 site/publish_ssh.py my-vm /var/www/film ./site https://xxx.trycloudflare.com index.html media/film_web.mp4 media/film_en.vtt
"""
import os, subprocess, sys, urllib.request
from pathlib import Path

host, remote, local, url, *files = sys.argv[1:]
# Git Bash (MSYS) rewrites "/var/www/x" into "C:/Program Files/Git/var/www/x" before Python sees it; run with
# MSYS_NO_PATHCONV=1, or from PowerShell. Refuse anything that is not a plain POSIX path.
if not remote.startswith("/") or ":" in remote or " " in remote:
    raise SystemExit(f"remote dir looks rewritten or unsafe: {remote!r} (Git Bash? set MSYS_NO_PATHCONV=1)")
ssh = r"C:\windows\System32\OpenSSH\ssh.exe" if os.name == "nt" else "ssh"
tar = r"C:\windows\System32\tar.exe" if os.name == "nt" else "tar"
for f in files:
    if not (Path(local) / f).exists(): raise SystemExit(f"missing {f}")
p_tar = subprocess.Popen([tar, "-cf", "-", "-C", local, *files], stdout=subprocess.PIPE)
r = subprocess.run([ssh, "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, f"mkdir -p {remote} && tar -xf - -C {remote}"], stdin=p_tar.stdout)
p_tar.wait()
if r.returncode or p_tar.returncode: raise SystemExit("upload failed")
print("uploaded", len(files), "files")


def head_range(u, rng):
    req = urllib.request.Request(u, headers={"Range": f"bytes={rng}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, resp.headers.get("Content-Range", ""), len(resp.read())


ok = True
for f in files:
    u = f"{url.rstrip('/')}/{f}"
    size = (Path(local) / f).stat().st_size
    if f.endswith(".mp4"):
        s1, cr, _ = head_range(u, "0-1023")
        s2, _, n2 = head_range(u, f"{size - 1024}-{size - 1}")
        good = s1 == 206 and s2 == 206 and n2 == 1024 and cr.endswith(f"/{size}")
        print(f"{'OK ' if good else 'BAD'} {f}  ranges {s1}/{s2}  {cr}")
    else:
        with urllib.request.urlopen(u, timeout=60) as resp:
            n = len(resp.read()); good = resp.status == 200 and n == size
        print(f"{'OK ' if good else 'BAD'} {f}  {n} bytes (local {size})")
    ok &= good
sys.exit(0 if ok else 1)
