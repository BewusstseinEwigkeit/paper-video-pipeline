"""Check every narration anchor in the picture code against the generated timeline.

The picture never uses absolute seconds: scenes call at("<line id>", "<phrase>") and the time comes from the narration's
word timings (src/film/data/vo.ts). After any script or voice change, run this before rendering:
  * BAD  : at() names a line that no longer exists, or a phrase that is no longer spoken in that line;
  * WARN : a bare number >= 20 in a timing position (e.g. `fade(t, 121.4, ...)`, `const T0 = 206.05`) - a hard-coded
           second that will silently drift when the narration changes. Wrap it in an at() expression instead.
usage: python -X utf8 tools/check_anchors.py src/film src/film/data/vo.ts      (exit 1 on BAD)
"""
import json, re, sys
from pathlib import Path
from textutil import norm

src, vo_ts = Path(sys.argv[1]), Path(sys.argv[2])
txt = vo_ts.read_text(encoding="utf-8")
VO = json.loads(txt[txt.index("= {", txt.index("export const VO:")) + 2: txt.rindex("}") + 1])
joined = {k: "".join(norm(w[0]) for w in v["words"]) for k, v in VO.items()}

bad = warn = 0
TIMING = re.compile(r"(?:fade|ramp|ease)\(\s*t\s*,[^)]*?\b(\d{2,4}\.\d+)\b|const\s+\w*(?:T0|T1|_T\w*|t0|t1|Start|End)\s*=\s*(\d{2,4}\.\d+)\s*;")
for f in sorted(src.rglob("*.ts*")):
    if "data" in f.parts: continue
    code = f.read_text(encoding="utf-8")
    for m in re.finditer(r'\bat\(\s*"([\w-]+)"(?:\s*,\s*"([^"]*)")?', code):
        lid, phrase = m.group(1), m.group(2)
        ln = code[: m.start()].count("\n") + 1
        if lid not in VO:
            print(f"BAD  {f}:{ln}  line {lid!r} not in narration"); bad += 1
        elif phrase and norm(phrase) not in joined[lid]:
            print(f"BAD  {f}:{ln}  {phrase!r} not spoken in {lid}: {VO[lid]['text']}"); bad += 1
    for m in TIMING.finditer(code):
        v = float(m.group(1) or m.group(2))
        if v >= 20:
            ln = code[: m.start()].count("\n") + 1
            print(f"WARN {f}:{ln}  hard-coded time {v}"); warn += 1
print(f"{bad} bad, {warn} warnings, {len(VO)} narration lines, total {VO and max(v['end'] for v in VO.values()):.1f}s")
sys.exit(1 if bad else 0)
