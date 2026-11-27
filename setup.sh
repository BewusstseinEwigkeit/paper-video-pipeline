#!/usr/bin/env bash
# paper-video-pipeline one-click setup for macOS / Linux:   bash setup.sh
# Checks Python 3.10+, Node 20+, ffmpeg (Homebrew installs missing ones on macOS), installs the Python packages
# (into the active conda / venv, otherwise into ./.venv), runs npm install in template/, downloads the small Whisper
# model, installs the agent skill for Claude Code / Codex / Gemini CLI / Antigravity, and runs a smoke test.
# Options: --no-install  --no-model  --no-skill  --force-skill        Env: SKILL_HOME (default: $HOME)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NO_INSTALL=0; NO_MODEL=0; NO_SKILL=0; FORCE_SKILL=0; USE_VENV=0
for a in "$@"; do case "$a" in
  --no-install) NO_INSTALL=1 ;; --no-model) NO_MODEL=1 ;; --no-skill) NO_SKILL=1 ;; --force-skill) FORCE_SKILL=1 ;;
  *) echo "unknown option $a"; exit 2 ;; esac; done
SKILL_HOME="${SKILL_HOME:-$HOME}"
WARN=0
step() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '    \033[32mok\033[0m  %s\n' "$1"; }
warn() { printf '    \033[33m!!\033[0m  %s\n' "$1"; WARN=$((WARN + 1)); }
fail() { printf '    \033[31mxx\033[0m  %s\n' "$1"; exit 1; }
brew_ok() { [ "$NO_INSTALL" = 0 ] && command -v brew >/dev/null 2>&1; }

step "Python 3.10+"
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  brew_ok || fail "Python 3.10+ not found. Install it (macOS: brew install python@3.12; Ubuntu: sudo apt install python3 python3-venv)."
  brew install python@3.12; PY=python3.12
fi
if [ -z "${VIRTUAL_ENV:-}" ] && [ -z "${CONDA_PREFIX:-}" ]; then
  # system / Homebrew Pythons refuse global pip installs (PEP 668): use a local venv
  [ -x "$REPO/.venv/bin/python" ] || "$PY" -m venv "$REPO/.venv" \
    || fail "could not create .venv (Debian/Ubuntu: sudo apt install python3-venv), or activate a conda / venv first"
  PY="$REPO/.venv/bin/python"; USE_VENV=1
fi
ok "$("$PY" -c 'import sys; print(sys.version.split()[0], sys.executable)')"

step "Node.js 20+"
major() { if command -v node >/dev/null 2>&1; then node -v | sed 's/^v//; s/\..*//'; else echo 0; fi; }
if [ "$(major)" -lt 20 ] && brew_ok; then echo "    installing Node.js with brew"; brew install node; fi
[ "$(major)" -ge 20 ] || fail "Node.js 20+ required (found $(node -v 2>/dev/null || echo none)). See https://nodejs.org"
ok "node $(node -v)"

step "ffmpeg and ffprobe"
if ! command -v ffmpeg >/dev/null 2>&1; then
  brew_ok || fail "ffmpeg not found. Install it (macOS: brew install ffmpeg; Ubuntu: sudo apt install ffmpeg)."
  brew install ffmpeg
fi
command -v ffprobe >/dev/null 2>&1 || fail "ffprobe missing (it ships with ffmpeg)"
ok "$(ffmpeg -version | head -1)"

step "Python packages (requirements.txt)"
"$PY" -m pip install --disable-pip-version-check -r "$REPO/requirements.txt"
ok "numpy, faster-whisper, edge-tts, pillow"

step "Remotion template (npm install)"
(cd "$REPO/template" && npm install --no-audit --no-fund) || fail "npm install failed (behind a firewall? npm config set registry <mirror>)"
(cd "$REPO/template" && npx remotion browser ensure) || warn "could not download the Remotion headless browser; rendering will retry, or set PVP_BROWSER to an installed Chrome"
ok "template/node_modules and the Remotion headless browser"

if [ "$NO_MODEL" = 0 ]; then
  step "Whisper model for word timing (small.en, about 0.5 GB, once)"
  if "$PY" -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8'); print('ready')"; then ok "small.en cached"
  else warn "Whisper model download failed. If huggingface.co is blocked: export HF_ENDPOINT=https://hf-mirror.com and run setup again."; fi
fi

step "Edge TTS reachability"
if "$PY" -c "import asyncio, os, edge_tts; p = next((os.environ[k] for k in ('HTTPS_PROXY','https_proxy','ALL_PROXY','all_proxy','HTTP_PROXY','http_proxy') if os.environ.get(k)), None); asyncio.run(edge_tts.Communicate('ok', 'en-US-AndrewNeural', proxy=p).save(os.path.join(__import__('tempfile').gettempdir(), 'pvp_edge_check.mp3'))); print('synthesis ok')"; then ok "edge-tts works"
else warn "edge-tts could not reach speech.platform.bing.com; voicing needs that connection."; fi

if [ "$NO_SKILL" = 0 ]; then
  step "Agent skill"
  SRC="$REPO/skills/paper-video-pipeline"; n=0
  REPO_ESC=$(printf '%s' "$REPO" | sed 's/[&|\\]/\\&/g')
  for agent in .claude .codex .agents .gemini; do
    [ -d "$SKILL_HOME/$agent" ] || continue
    DST="$SKILL_HOME/$agent/skills/paper-video-pipeline"
    if [ -e "$DST" ] && [ ! -e "$DST/.installed-by-setup" ] && [ "$FORCE_SKILL" = 0 ]; then
      warn "$DST already exists and was not made by this setup; left untouched (--force-skill overwrites)"; continue; fi
    mkdir -p "$DST"
    for f in "$SRC"/*; do [ "$(basename "$f")" = SKILL.md ] || cp -R "$f" "$DST/"; done
    sed "s|{{REPO_DIR}}|$REPO_ESC|g" "$SRC/SKILL.md" > "$DST/SKILL.md"
    printf '%s' "$REPO" > "$DST/.installed-by-setup"
    ok "-> $DST"; n=$((n + 1))
  done
  [ "$n" -gt 0 ] || warn "no agent folder found (~/.claude, ~/.codex, ~/.agents, ~/.gemini)"
fi

step "Smoke test"
(cd "$REPO/template" && "$PY" ../tools/fake_timeline.py narration.example.json src/film/data/vo.ts \
  && "$PY" ../tools/check_anchors.py src/film src/film/data/vo.ts && npx tsc --noEmit) || fail "smoke test failed"
ok "timeline, anchors and type check pass"

echo
if [ "$WARN" = 0 ]; then echo "All set."; else echo "Done with $WARN warning(s) above."; fi
if [ "$USE_VENV" = 1 ]; then echo "Python packages are in .venv: run 'source $REPO/.venv/bin/activate' before using the tools."; fi
cat <<'EOF'

Next:
  cd template
  npx remotion studio                                   # preview the example film
  python -X utf8 ../tools/tts_edge.py narration.example.json out/vo      # voice it (free Edge TTS)
  python -X utf8 ../tools/assemble_natural.py narration.example.json out/vo public/audio/vo.wav src/film/data/vo.ts
Chinese: use narration.zh.example.json. Full steps: README.md. In Claude Code / Codex, just ask for a paper video.
EOF
