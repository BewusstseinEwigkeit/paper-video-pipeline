"""Final mix: narration + music bed with hand-drawn (look-ahead) volume automation. Stereo 48 kHz PCM WAV out.

usage: python -X utf8 tools/mix_all.py public/audio/vo.wav music.mp3 public/audio/final.wav

If the music is shorter than the narration it is slowed with atempo (down to 0.90x, inaudible on ambient piano);
anything shorter than that is an error: pick a longer track or loop it by hand (zero-padding would cut the bed off
before the closing line).

Why not sidechaincompress: a compressor reacts AFTER the voice starts, so the piano drops audibly on the first syllable
and pumps between sentences. Here the music is automated like an editor would ride a fader:
  * speech regions = voiced frames merged across pauses shorter than MERGE (short pauses never lift the music);
  * the bed starts ducking DUCK_LEAD s before each region and is fully down just before the first word;
  * after a region it releases slowly; in short gaps the release and the next duck overlap, so it only half-lifts;
  * music stays stereo (no mono fold-down), voice is centred; one loudness/peak trim at the end; no lossy encode.
No synthesized sound effects: transitions are carried by the music lifting in chapter gaps.
"""
import subprocess, sys, wave
import numpy as np

SR = 48000
G_OPEN, G_UNDER = -4.0, -12.5        # music gain (dB) in the open / under narration
MERGE, DUCK_LEAD, DUCK_LEN, REL_DELAY, REL_LEN = 1.2, 0.95, 0.85, 0.15, 0.9  # chapter gaps (~1.7 s) get one slow musical swell
FADE_IN, FADE_OUT = 1.2, 4.0
TARGET_SPEECH_RMS = -20.0            # dBFS of the voice while talking (online video ~ -16 LUFS integrated)

vo_p, mu_p, out_p = sys.argv[1:4]


def load(p, ch):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).copy()


vo = load(vo_p, 1)[:, 0]
N = len(vo)
mu = load(mu_p, 2)
if len(mu) < N:
    tempo = len(mu) / N * 0.998
    if tempo < 0.90:
        raise SystemExit(f"music {len(mu)/SR:.1f}s is too short for narration {N/SR:.1f}s (needs atempo {tempo:.3f} < 0.90)")
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", mu_p, "-af", f"atempo={tempo:.5f}", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    mu = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    print(f"music stretched with atempo={tempo:.4f} to {len(mu)/SR:.1f}s")
mu = mu[:N]
if len(mu) < N: mu = np.concatenate([mu, np.zeros((N - len(mu), 2), np.float32)])

# voice activity on 10 ms frames
hop = SR // 100; nf = N // hop
rms = np.sqrt(np.mean(vo[: nf * hop].reshape(nf, hop) ** 2, axis=1) + 1e-12)
voiced = 20 * np.log10(rms) > -38
regions, s, last = [], None, -1e9
for i, v in enumerate(voiced):
    if not v: continue
    t = i / 100
    if s is None: s = t
    elif t - last > MERGE: regions.append((s, last)); s = t
    last = t
if s is not None: regions.append((s, last))

# duck weight w(t) in [0, 1]: max over regions of a smooth trapezoid with look-ahead
tt = np.arange(nf) / 100
sm = lambda x: 0.5 - 0.5 * np.cos(np.pi * np.clip(x, 0, 1))
w = np.zeros(nf)
for a, b in regions:
    up = sm((tt - (a - DUCK_LEAD)) / DUCK_LEN)
    down = 1 - sm((tt - (b + REL_DELAY)) / REL_LEN)
    w = np.maximum(w, np.minimum(up, down))
g_db = G_OPEN + (G_UNDER - G_OPEN) * w
g = np.interp(np.arange(N) / SR, tt, 10 ** (g_db / 20))
g *= np.clip(np.arange(N) / (FADE_IN * SR), 0, 1) ** 2                          # fade in
g *= np.clip((N - np.arange(N)) / (FADE_OUT * SR), 0, 1) ** 1.5                 # fade out at the very end
music = mu * g[:, None]

# voice: gentle 70 Hz high-pass (rumble only), then level so speech sits at TARGET
X = np.fft.rfft(vo); fr = np.fft.rfftfreq(N, 1 / SR); X *= 1 / np.sqrt(1 + (70 / np.maximum(fr, 1)) ** 4); vo = np.fft.irfft(X, N)
sp = np.repeat(voiced, hop)[:N]; sp = np.concatenate([sp, np.zeros(N - len(sp), bool)])
k = 10 ** ((TARGET_SPEECH_RMS - 20 * np.log10(np.sqrt(np.mean(vo[sp] ** 2)) + 1e-12)) / 20)
mix = music * k + (vo * k)[:, None]
pk = np.abs(mix).max()
if pk > 10 ** (-1.0 / 20): mix *= 10 ** (-1.0 / 20) / pk                      # keep 1 dB headroom
with wave.open(out_p, "wb") as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
mus_sp = 20 * np.log10(np.sqrt(np.mean((music[sp] * k) ** 2)) + 1e-12)
mus_open = 20 * np.log10(np.sqrt(np.mean((music[~sp][SR * 2:] * k) ** 2)) + 1e-12)
print(f"regions {len(regions)}  voice {TARGET_SPEECH_RMS} dB  music under speech {mus_sp:.1f} dB  music in gaps {mus_open:.1f} dB  peak {20*np.log10(np.abs(mix).max()):.1f} dB  -> {out_p}")
