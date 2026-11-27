"""Section-level narration with Microsoft Edge TTS: free, no account or key, English and Chinese voices.

Each section (all lines whose id starts with the same letter) is synthesized in ONE request, so intonation flows across
sentences, then converted once to 48 kHz mono PCM: out/vo/_sec_<key>.wav, the same files assemble_natural.py reads after
tools/tts_gemini.py. Edge voices take no director's note; the section "note" is only used by the Gemini engine.

usage: python -X utf8 tools/tts_edge.py narration.json out/vo [section keys...]
  narration.json "lang": "en" (default) or "zh";  "tts": {"voice": "...", "rate": "+0%", "pitch": "+0Hz"}
  default voices: en-US-AndrewNeural (English), zh-CN-YunyangNeural (Chinese). List all: python -m edge_tts --list-voices
Re-synthesizing one section only re-runs that key, e.g. `... out/vo r`; the other takes are kept.
"""
import asyncio, json, os, subprocess, sys, tempfile, time
from pathlib import Path

import edge_tts
from textutil import lang_of

DEFAULT_VOICE = {"en": "en-US-AndrewNeural", "zh": "zh-CN-YunyangNeural", "ja": "ja-JP-KeitaNeural", "ko": "ko-KR-InJoonNeural"}

spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
LANG = lang_of(spec)
tts = spec.get("tts", {})
VOICE = tts.get("voice", "")
if "Neural" not in VOICE:  # empty, or a Gemini voice name left over from an older narration file
    if VOICE: print(f"note: {VOICE!r} is not an Edge voice; using the default for {LANG!r}")
    VOICE = DEFAULT_VOICE.get(LANG.split("-")[0], DEFAULT_VOICE["en"])
RATE, PITCH = tts.get("rate", "+0%"), tts.get("pitch", "+0Hz")
# the websocket does not read proxy variables by itself; pass them through (needed behind HTTP proxies)
PROXY = next((os.environ[k] for k in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy") if os.environ.get(k)), None)
SECTIONS = [s["key"] for s in spec["sections"]]
want = set(sys.argv[3:]) or set(SECTIONS)


async def synth(text, mp3):
    await edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, proxy=PROXY).save(str(mp3))


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


print(f"voice {VOICE}  rate {RATE}  lang {LANG}" + (f"  proxy {PROXY}" if PROXY else ""))
total = 0.0
for sec in SECTIONS:
    if sec not in want: continue
    ls = [l for l in spec["lines"] if l["id"].startswith(sec)]
    if not ls: continue
    wav = out / f"_sec_{sec}.wav"
    text = "\n".join(l.get("say", l["text"]) for l in ls)
    with tempfile.TemporaryDirectory() as td:
        mp3 = Path(td) / "take.mp3"
        for i in range(5):
            try:
                asyncio.run(synth(text, mp3)); break
            except Exception as e:  # network hiccups are common; the service itself is stable
                print(f"  retry {i + 1}: {type(e).__name__}: {e}"); time.sleep(2 + 3 * i)
        else:
            raise SystemExit("edge-tts failed: check the network (it needs speech.platform.bing.com)")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)], check=True)
    d = dur(wav); total += d
    print(f"[{sec}] {len(ls)} lines -> {wav.name} {d:5.1f}s")
(out / "meta.json").write_text(json.dumps({"engine": "edge", "voice": VOICE, "lang": LANG}), encoding="utf-8")
print(f"done, {total:.1f}s of speech")
