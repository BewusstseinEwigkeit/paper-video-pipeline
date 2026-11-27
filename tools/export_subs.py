"""Export SRT + WebVTT (and the word-timing JSON a web player can use) from the generated timeline.

Cues are chunked like the on-screen captions: <= 64 characters (about 22 for Chinese), split at sentence ends, colons
and late commas.
usage: python -X utf8 tools/export_subs.py src/film/data/vo.ts out/film_en   ->  film_en.srt, film_en.vtt, film_en.words.json
"""
import json, re, sys
from pathlib import Path
from textutil import join, width

vo_ts, stem = Path(sys.argv[1]), Path(sys.argv[2])
txt = vo_ts.read_text(encoding="utf-8")
vo = json.loads(txt[txt.index("= {", txt.index("export const VO:")) + 2: txt.rindex("}") + 1])
CJK_TEXT = any(width(l["text"]) > len(l["text"]) for l in vo.values())
MAX = 44 if CJK_TEXT else 64
segs = []
for l in vo.values():
    cur = []
    for i, w in enumerate(l["words"]):
        if cur and width(join([x[0] for x in cur] + [w[0]])) > MAX:
            segs.append(cur); cur = []
        cur.append(w)
        line = join([x[0] for x in cur])
        if (re.search(r"[.?!:;。？！：；]$", w[0]) or (re.search(r"[,，、]$", w[0]) and width(line) > MAX * 0.55)) and i < len(l["words"]) - 1:
            segs.append(cur); cur = []
    if cur: segs.append(cur)
cues = [(c[0][1], c[-1][2] + 0.2, join([w[0] for w in c])) for c in segs]


def ts(s, sep):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


stem.parent.mkdir(parents=True, exist_ok=True)
Path(f"{stem}.srt").write_text("\n".join(f"{i}\n{ts(a, ',')} --> {ts(b, ',')}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")
Path(f"{stem}.vtt").write_text("WEBVTT\n\n" + "\n".join(f"{i}\n{ts(a, '.')} --> {ts(b, '.')}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")
Path(f"{stem}.words.json").write_text(json.dumps(vo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(len(cues), "cues ->", f"{stem}.srt / .vtt / .words.json")
