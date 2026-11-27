"""Section-level narration with Gemini TTS (Google Cloud Text-to-Speech, model gemini-*-tts).

Each section (all lines whose id starts with the same letter) is synthesized in ONE request with its own director's
note, so intonation flows across sentences. faster-whisper word times are aligned to the text and every line is cut at
the middle of its inter-line pause (<id>.mp3 + timings.json are for inspection; assemble_natural.py uses _sec_*.wav).

Optional engine: the default voice is the free Edge TTS (tools/tts_edge.py). Use this one for Gemini's directable voices.
usage: python -X utf8 tools/tts_gemini.py narration.json out/vo [section keys...]
  narration.json -> see narration.example.json: "tts_gemini" (model, voice, base_prompt, language_code), "sections"
  (ordered keys + note), "lines" (id, text, optional "say" respelling for acronyms / numbers), "lang" (en / zh).
  An older file whose "tts" block holds the Gemini model / voice still works.
auth: gcloud user token on the active project (Text-to-Speech API enabled). Re-synthesizing one section only
re-runs that key, e.g. `... out/vo r` after a results-line edit; the other takes are kept.
"""
import base64, difflib, json, os, re, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

import numpy as np
from textutil import lang_of, norm, tokens, whisper_lang, whisper_model, whisper_prompt

DEFAULT_BASE = (
    "You are the narrator of a polished research showcase film for a computer-vision conference, in the style of a "
    "high-end science documentary. Natural, intelligent, engaged; vary pitch and pace with the meaning; never read "
    "like a list; no theatrical trailer voice, no breathiness. Acronyms are spelled letter by letter exactly as written "
    "with hyphens. Use a clear, supported chest voice: no vocal fry or creaky voice. Pause only where there is "
    "punctuation; never pause between a subject and its verb or after a preposition. Leave a real breath between "
    "sentences. Overall pace: a brisk, fluent documentary delivery of about 150 words per minute; do not linger. "
)

spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
LANG = lang_of(spec)
tts = spec.get("tts_gemini")
if tts is None:  # older narration files kept the Gemini settings under "tts"
    tts = spec.get("tts", {}) if "Neural" not in spec.get("tts", {}).get("voice", "") else {}
LANGUAGE_CODE = tts.get("language_code", {"en": "en-US", "zh": "cmn-CN", "ja": "ja-JP", "ko": "ko-KR"}.get(LANG.split("-")[0], LANG))
MODEL = tts.get("model", "gemini-3.1-flash-tts-preview")
VOICE = tts.get("voice", "Charon")
BASE = tts.get("base_prompt", DEFAULT_BASE)
SECTIONS = [(s["key"], s.get("note", "")) for s in spec["sections"]]
want = set(sys.argv[3:]) or {k for k, _ in SECTIONS}
tf = out / "timings.json"
timings = json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else {}

g = lambda *a: subprocess.run(["gcloud.cmd" if os.name == "nt" else "gcloud", *a], capture_output=True, text=True).stdout.strip()
TOK, PROJ = g("auth", "print-access-token"), g("config", "get-value", "project")


def synth(text, prompt, path):
    body = {"input": {"prompt": prompt, "text": text}, "voice": {"languageCode": LANGUAGE_CODE, "name": VOICE, "model_name": MODEL},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 48000}}
    for i in range(6):
        req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {TOK}", "x-goog-user-project": PROJ, "Content-Type": "application/json"})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=300))
            path.write_bytes(base64.b64decode(r["audioContent"])); return
        except urllib.error.HTTPError as e:
            raise SystemExit(f"HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}")
        except Exception as e:
            print("  retry", i + 1, type(e).__name__); time.sleep(3 + 3 * i)
    raise SystemExit("tts failed")


_model = None
def pcm16k(wav):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(wav), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def words_of(wav):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(whisper_model(LANG), device="cpu", compute_type="int8")
    segs, _ = _model.transcribe(pcm16k(wav), word_timestamps=True, language=whisper_lang(LANG), beam_size=5,
                                initial_prompt=whisper_prompt(LANG))
    return [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]




def align(cw, ww):
    """text words -> (start, end) via char-level matching against whisper words; gaps interpolated."""
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
            t0 = res[lo][1] if lo is not None else 0.0; t1 = res[hi][0] if hi is not None else t0 + 0.4
            res[i] = [t0, t1]
    return res


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


lines = spec["lines"]
for sec, note in SECTIONS:
    if sec not in want: continue
    ls = [l for l in lines if l["id"].startswith(sec)]
    if not ls: continue
    wav = out / f"_sec_{sec}.wav"
    print(f"[{sec}] synth {len(ls)} lines")
    if os.environ.get("RESPLIT") and wav.exists():
        print("  reuse existing take", wav.name)  # re-split an approved take without re-synthesizing
    else:
        synth("\n".join(l.get("say", l["text"]) for l in ls), BASE + note, wav)
    D = dur(wav)
    ww = words_of(wav)
    say_words = [(li, w) for li, l in enumerate(ls) for w in tokens(l.get("say", l["text"]), LANG)]
    tim = align([w for _, w in say_words], ww)
    first, last = {}, {}
    for (li, _), (s, e) in zip(say_words, tim):
        first.setdefault(li, s); last[li] = e
    xx = pcm16k(wav); nf = len(xx) // 160
    quiet = 20 * np.log10(np.sqrt(np.mean(xx[: nf * 160].reshape(nf, 160) ** 2, axis=1) + 1e-12)) < -42

    def best_cut(t0, t1):
        i0, i1 = max(0, int(t0 * 100)), min(nf, int(t1 * 100))
        best, cur = (0, i0, i0), None
        for i in range(i0, i1):
            if quiet[i] and cur is None: cur = i
            if (not quiet[i] or i == i1 - 1) and cur is not None:
                if i - cur > best[0]: best = (i - cur, cur, i)
                cur = None
        if best[0] > 0: return (best[1] + best[2]) / 2 / 100
        e = np.sqrt(np.mean(xx[i0 * 160: i1 * 160].reshape(-1, 160) ** 2, axis=1)); return (i0 + int(np.argmin(e))) / 100

    cuts = [0.0] + [best_cut(last[i] - 0.25, first[i + 1] + 0.25) for i in range(len(ls) - 1)] + [D]
    for i, l in enumerate(ls):
        a, b = max(0.0, cuts[i]), cuts[i + 1]
        mp3 = out / f"{l['id']}.mp3"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(wav),
                        "-af", "afade=t=in:d=0.02,areverse,afade=t=in:d=0.04,areverse", "-ar", "48000", "-b:a", "192k", str(mp3)], check=True)
        cap = tokens(l["text"], LANG)
        ctim = align(cap, [(w, s - a, e - a) for w, s, e in ww if a - 0.05 <= s <= b + 0.05])
        timings[l["id"]] = {"text": l["text"], "say": l.get("say", l["text"]), "duration": round(dur(mp3), 3),
                            "words": [[w, round(max(0, s), 3), round(max(0, e), 3)] for w, (s, e) in zip(cap, ctim)]}
        print(f"  {l['id']} {timings[l['id']]['duration']:5.2f}s")
    print("  heard:", " ".join(w for w, _, _ in ww)[:400])
    tf.write_text(json.dumps({l["id"]: timings[l["id"]] for l in lines if l["id"] in timings}, ensure_ascii=False, indent=1), encoding="utf-8")
(out / "meta.json").write_text(json.dumps({"engine": "gemini", "voice": VOICE, "lang": LANG}), encoding="utf-8")
print("total speech", round(sum(v["duration"] for v in timings.values()), 2))
