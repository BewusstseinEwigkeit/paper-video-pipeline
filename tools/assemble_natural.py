"""Assemble the narration from the section-level TTS takes, keeping the speaker's own pauses.

Each section take stays continuous PCM (re-encoding MP3 or squeezing every pause to one length sounds rushed and
slightly "digital"):
  * pauses longer than CAP are shortened (middle removed, 30 ms equal-power crossfade, so no clicks);
  * sections are laid on one timeline with a chapter breath between them;
  * a few lines get EXTRA seconds inserted in the middle of their natural pause (room for a visual beat);
  * word times come from faster-whisper on the section take (cached), aligned to the caption text.
Outputs a 48 kHz PCM WAV (no lossy step) and the TS timeline module the picture reads.

usage: python -X utf8 tools/assemble_natural.py narration.json out/vo public/audio/vo.wav src/film/data/vo.ts
Timeline knobs live in narration.json -> "timeline": lead, tail, cap, chapter_gap {section: s}, extra {line id: s}.
Language: narration.json "lang" ("en" default, "zh" for Chinese); see textutil.py for how Chinese text is tokenized.
"""
import difflib, json, re, subprocess, sys, wave
from pathlib import Path
import numpy as np
from textutil import lang_of, norm, tokens, whisper_lang, whisper_model, whisper_prompt

SR = 48000
THR = -42.0           # dBFS RMS on 10 ms frames counts as silence

spec, src, out_wav, out_ts = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
SPEC = json.loads(spec.read_text(encoding="utf-8"))
lines = SPEC["lines"]
TL = SPEC.get("timeline", {})
LEAD = TL.get("lead", 7.0)          # music-only cold open before the first word
TAIL = TL.get("tail", 2.6)          # room after the last word
CAP = TL.get("cap", 0.95)           # longest pause kept inside a section (natural takes rarely exceed ~1.1 s)
CH_GAP = TL.get("chapter_gap", {})  # silence before a section (voiced end -> onset); default 1.7 s
EXTRA = TL.get("extra", {})         # seconds added inside the natural pause before a line (room for a visual beat)
ORDER = [s["key"] for s in SPEC["sections"]]
LANG = lang_of(SPEC)


def load(p):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


_model = None
def whisper_words(wav, hint=""):
    cache = wav.with_suffix(".words.json" if LANG.startswith("en") else f".words.{LANG}.json")
    if cache.exists() and cache.stat().st_mtime > wav.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(whisper_model(LANG), device="cpu", compute_type="int8")
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(wav), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = _model.transcribe(np.frombuffer(raw, np.float32), word_timestamps=True, language=whisper_lang(LANG), beam_size=5,
                                initial_prompt=whisper_prompt(LANG, hint))
    ww = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    cache.write_text(json.dumps(ww), encoding="utf-8")
    return ww


def align(cw, ww, t_lo=0.0):
    """caption words -> [start, end] via char-level matching against whisper words; gaps interpolated."""
    cstr, cown = "", []
    for i, w in enumerate(cw):
        n = norm(w); cstr += n; cown += [i] * len(n)
    wstr, wt = "", []
    for w, s, e in ww:
        n = norm(w)
        for k in range(len(n)): wstr += n[k]; wt.append(s + (e - s) * (k + 0.5) / max(1, len(n)))
    tt = [[] for _ in cw]
    for a, b, size in difflib.SequenceMatcher(None, cstr, wstr, autojunk=False).get_matching_blocks():
        for k in range(size): tt[cown[a + k]].append(wt[b + k])
    res = [[min(x), max(x)] if x else None for x in tt]
    known = [i for i, r in enumerate(res) if r]
    for i, r in enumerate(res):
        if r is None:
            lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
            t0 = res[lo][1] if lo is not None else (min(t_lo, res[hi][0]) if hi is not None else t_lo); t1 = res[hi][0] if hi is not None else t0 + 0.4
            res[i] = [t0, t1]
    return res


def quiet_mask(x):
    n = len(x) // 480
    return 20 * np.log10(np.sqrt(np.mean(x[: n * 480].reshape(n, 480) ** 2, axis=1)) + 1e-12) < THR


def runs(mask):
    out, s = [], None
    for i, m in enumerate(mask):
        if m and s is None: s = i
        if not m and s is not None: out.append((s / 100, i / 100)); s = None
    if s is not None: out.append((s / 100, len(mask) / 100))
    return out


def xfade_join(parts, ms=20):
    """concatenate PCM parts; every join sits inside silence, so a short cosine fade-out / fade-in on each side
    removes any discontinuity (no click) without changing the length (word times stay exact)."""
    n = int(SR * ms / 1000); out = []
    for j, p in enumerate(parts):
        p = p.copy(); k = min(n, len(p) // 2); w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k))
        if j > 0: p[:k] *= w
        if j < len(parts) - 1: p[-k:] *= w[::-1]
        out.append(p)
    return np.concatenate(out)


timeline, T = [], {}
cursor = LEAD
timeline.append(np.zeros(int(LEAD * SR), np.float32))
report = []
for si, sec in enumerate(ORDER):
    ls = [l for l in lines if l["id"].startswith(sec)]
    if not ls: continue
    wav = src / f"_sec_{sec}.wav"
    x = load(wav); D = len(x) / SR
    ww = whisper_words(wav, "".join(l["text"] for l in ls))
    say = [(li, w) for li, l in enumerate(ls) for w in tokens(l.get("say", l["text"]), LANG)]
    tim = align([w for _, w in say], ww)
    first, last = {}, {}
    for (li, _), (s, e) in zip(say, tim): first.setdefault(li, s); last[li] = e
    q = quiet_mask(x); sil = runs(q)
    voiced = [(a, b) for a, b in zip([0] + [e for _, e in sil], [s for s, _ in sil] + [D]) if b - a > 0.03]
    on, off = voiced[0][0], voiced[-1][1]
    # line boundaries = middle of the longest silent run between consecutive lines
    def best_cut(t0, t1):
        cand = [(b - a, (a + b) / 2) for a, b in sil if a < t1 and b > t0]
        return max(cand)[1] if cand else (t0 + t1) / 2
    cuts = [best_cut(last[i] - 0.25, first[i + 1] + 0.25) for i in range(len(ls) - 1)]
    # keep-segments: [on - 0.15, off + 0.35], shortening long inner pauses and opening EXTRA at line cuts
    a0, b0 = max(0.0, on - 0.15), min(D, off + 0.35)
    edits = []  # (silence start, silence end, kept length)
    for s0, s1 in sil:
        if s1 <= a0 + 0.2 or s0 >= b0 - 0.4: continue
        cut_here = [i for i, c in enumerate(cuts) if s0 <= c <= s1]
        keep = min(s1 - s0, CAP)
        if cut_here: keep += EXTRA.get(ls[cut_here[0] + 1]["id"], 0.0)
        if abs(keep - (s1 - s0)) > 0.02: edits.append((s0, s1, keep))
    parts, mapping, pos, acc = [], [], a0, 0.0  # mapping: (src_t0, src_t1, out_t0) linear pieces
    for s0, s1, keep in edits:
        if keep < s1 - s0:       # remove the middle
            m0, m1 = s0 + keep / 2, s1 - keep / 2
            parts.append(x[int(pos * SR): int(m0 * SR)]); mapping.append((pos, m0, acc)); acc += m0 - pos; pos = m1
        else:                    # stretch the pause with true silence (the take's own room tone is ~-65 dB)
            mid = (s0 + s1) / 2
            parts.append(x[int(pos * SR): int(mid * SR)]); mapping.append((pos, mid, acc)); acc += mid - pos
            parts.append(np.zeros(int((keep - (s1 - s0)) * SR), np.float32)); acc += keep - (s1 - s0); pos = mid
    parts.append(x[int(pos * SR): int(b0 * SR)]); mapping.append((pos, b0, acc))
    y = xfade_join([p for p in parts if len(p)])

    def m(t):
        for p0, p1, o in mapping:
            if t <= p1: return o + max(0.0, t - p0)
        return mapping[-1][2] + (mapping[-1][1] - mapping[-1][0])

    if si > 0:
        gap = CH_GAP.get(sec, 1.7) - 0.15 - 0.35  # the section already carries 0.15 lead + 0.35 tail of room
        timeline.append(np.zeros(int(max(0, gap) * SR), np.float32)); cursor += max(0, gap)
    base = cursor
    q2 = quiet_mask(y)
    bounds = [0.0] + [m(c) for c in cuts] + [len(y) / SR]
    for i, l in enumerate(ls):
        lo, hi = bounds[i], bounds[i + 1]
        fr = np.where(~q2[int(lo * 100): int(hi * 100)])[0]
        von = lo + (fr[0] / 100 if len(fr) else 0); voff = lo + (fr[-1] / 100 + 0.01 if len(fr) else hi - lo)
        cap = tokens(l["text"], LANG)
        sub = [(w, m(s), m(e)) for w, s, e in ww if m(s) >= lo - 0.05 and m(s) <= hi + 0.05]
        ctim = align(cap, sub, von)
        T[l["id"]] = {"start": round(base + von - 0.1, 3), "end": round(base + voff + 0.15, 3), "text": l["text"],
                      "words": [[w, round(base + s, 3), round(base + e, 3)] for w, (s, e) in zip(cap, ctim)]}
    report.append(f"[{sec}] take {D:5.1f}s -> {len(y) / SR:5.1f}s, {len(edits)} pause edits")
    timeline.append(y.astype(np.float32)); cursor += len(y) / SR

timeline.append(np.zeros(int(TAIL * SR), np.float32))
vo = np.concatenate(timeline); total = round(len(vo) / SR, 3)
pcm = (np.clip(vo, -1, 1) * 32767).astype("<i2")
out_wav.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(out_wav), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
out_ts.write_text(
    "// Generated by tools/assemble_natural.py (natural section takes, word times from faster-whisper). Do not edit by hand.\n"
    "export type VoLine = { start: number; end: number; text: string; words: Array<[string, number, number]> };\n"
    f"export const VO_TOTAL = {total};\n"
    f"export const VO: Record<string, VoLine> = {json.dumps(T, ensure_ascii=False, indent=1)};\n", encoding="utf-8")
print("\n".join(report))
print("total", total, "s =", f"{int(total // 60)}:{total % 60:04.1f}", "lines", len(T))
