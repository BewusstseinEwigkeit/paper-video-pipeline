"""Re-transcribe section takes with a larger Whisper model to catch mispronunciations before anything is rendered.

The small model (used for word timing) mishears often ("Modeling" -> "Marling"); the medium model is the referee. Compare
its text with the script by eye: acronyms should come out letter by letter, numbers as numbers.
The language comes from out/vo/meta.json (written by tts_edge.py / tts_gemini.py); --lang zh overrides it.
usage: python -X utf8 tools/verify_voice.py out/vo [section keys...] [--lang zh]      (default: every _sec_*.wav)
"""
import json, subprocess, sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from textutil import whisper_lang, whisper_model, whisper_prompt

args = sys.argv[1:]
lang = None
if "--lang" in args:
    i = args.index("--lang"); lang = args[i + 1]; del args[i: i + 2]
d = Path(args[0])
keys = args[1:]
meta = d / "meta.json"
lang = (lang or (json.loads(meta.read_text(encoding="utf-8")).get("lang") if meta.exists() else None) or "en").lower()
files = [d / f"_sec_{k}.wav" for k in keys] if keys else sorted(d.glob("_sec_*.wav"))
m = WhisperModel(whisper_model(lang, big=True), device="cpu", compute_type="int8")
for f in files:
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(f), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = m.transcribe(np.frombuffer(raw, np.float32), beam_size=5, language=whisper_lang(lang), initial_prompt=whisper_prompt(lang))
    sep = "" if whisper_lang(lang) in ("zh", "ja") else " "
    print(f"== {f.name}\n{sep.join(s.text.strip() for s in segs)}\n")
