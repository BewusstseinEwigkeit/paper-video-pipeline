<#
paper-video-pipeline one-click setup for Windows (PowerShell 5.1 or 7).

  powershell -ExecutionPolicy Bypass -File setup.ps1

Checks Python 3.10+, Node 20+ and ffmpeg (installs missing ones with winget), pip-installs requirements.txt into the
active Python (conda / venv are respected), runs npm install in template/, downloads the small Whisper model, installs
the agent skill for Claude Code / Codex / Gemini CLI / Antigravity, and runs a smoke test.

Options:
  -NoInstall   do not winget-install missing tools, just report them
  -NoModel     skip the Whisper model download (about 0.5 GB, happens on first use instead)
  -NoSkill     do not install the agent skill
  -ForceSkill  overwrite an existing skill folder of the same name that this script did not create
  -SkillHome   where the agent folders live (default: your user profile)
This file must stay ASCII: Windows PowerShell 5.1 reads scripts in the ANSI code page.
#>
param([switch]$NoInstall, [switch]$NoModel, [switch]$NoSkill, [switch]$ForceSkill, [string]$SkillHome = $HOME)
$ErrorActionPreference = 'Stop'
$Repo = $PSScriptRoot
$Warnings = @()

function Step($m) { Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
function Ok($m) { Write-Host "    ok  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    !!  $m" -ForegroundColor Yellow; $script:Warnings += $m }
function Fail($m) { Write-Host "    xx  $m" -ForegroundColor Red; exit 1 }
function Add-SystemPath {
  # pick up tools winget just installed without dropping conda / venv entries of this session
  $env:Path = $env:Path + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Install-Tool($id, $what) {
  if ($NoInstall) { Fail "$what not found. Install it and run setup again." }
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Fail "$what not found and winget is not available. Install $what manually." }
  Write-Host "    installing $what with winget ($id) ..."
  winget install --id $id -e --silent --accept-source-agreements --accept-package-agreements | Out-Host
  Add-SystemPath
}

function Find-Python {
  foreach ($c in 'python', 'py', 'python3') {
    if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { continue }
    $a = @(); if ($c -eq 'py') { $a = @('-3') }
    $v = $null
    try { $v = & $c @a -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null } catch {}
    if ("$v" -match '^3\.(\d+)$' -and [int]$Matches[1] -ge 10) { $script:PyExe = $c; $script:PyArgs = $a; return $true }
  }
  return $false
}
function Py {
  & $script:PyExe @script:PyArgs @args
  if ($LASTEXITCODE -ne 0) { throw "python $($args -join ' ') failed with exit code $LASTEXITCODE" }
}
function Node-Major {
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) { return 0 }
  $v = (& node -v) -replace '^v', ''
  return [int]($v.Split('.')[0])
}

Step 'Python 3.10+'
if (-not (Find-Python)) { Install-Tool 'Python.Python.3.12' 'Python 3.12'; if (-not (Find-Python)) { Fail 'Python installed but not on PATH yet: open a new terminal and run setup again.' } }
Ok ("$script:PyExe " + (& $script:PyExe @script:PyArgs -c "import sys; print(sys.version.split()[0], sys.executable)"))

Step 'Node.js 20+'
if ((Node-Major) -lt 20) { Install-Tool 'OpenJS.NodeJS.LTS' 'Node.js LTS'; if ((Node-Major) -lt 20) { Fail 'Node.js 20+ not on PATH yet: open a new terminal and run setup again.' } }
Ok ("node " + (& node -v))

Step 'ffmpeg and ffprobe'
if (-not ((Get-Command ffmpeg -ErrorAction SilentlyContinue) -and (Get-Command ffprobe -ErrorAction SilentlyContinue))) {
  Install-Tool 'Gyan.FFmpeg' 'ffmpeg'
  if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Fail 'ffmpeg installed but not on PATH yet: open a new terminal and run setup again.' }
}
Ok ((& ffmpeg -version | Select-Object -First 1))

Step 'Python packages (requirements.txt)'
Py -m pip install --disable-pip-version-check -r (Join-Path $Repo 'requirements.txt')
Ok 'numpy, faster-whisper, edge-tts, pillow'

Step 'Remotion template (npm install)'
Push-Location (Join-Path $Repo 'template')
try {
  & npm.cmd install --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { Fail 'npm install failed (behind a firewall? set a registry with: npm config set registry <mirror>)' }
  & npx.cmd remotion browser ensure
  if ($LASTEXITCODE -ne 0) { Warn 'could not download the Remotion headless browser; rendering will retry, or set PVP_BROWSER to an installed Chrome' }
} finally { Pop-Location }
Ok 'template/node_modules and the Remotion headless browser'

if (-not $NoModel) {
  Step 'Whisper model for word timing (small.en, about 0.5 GB, once)'
  try {
    Py -c "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8'); print('ready')"
    Ok 'small.en cached'
  } catch {
    Warn 'Whisper model download failed. If huggingface.co is blocked, set $env:HF_ENDPOINT = "https://hf-mirror.com" and run setup again.'
  }
}

Step 'Edge TTS reachability'
try {
  Py -c "import asyncio, os, edge_tts; p = next((os.environ[k] for k in ('HTTPS_PROXY','https_proxy','ALL_PROXY','all_proxy','HTTP_PROXY','http_proxy') if os.environ.get(k)), None); asyncio.run(edge_tts.Communicate('ok', 'en-US-AndrewNeural', proxy=p).save(os.path.join(__import__('tempfile').gettempdir(), 'pvp_edge_check.mp3'))); print('synthesis ok')"
  Ok 'edge-tts works'
} catch { Warn 'edge-tts could not reach speech.platform.bing.com; voicing needs that connection.' }

if (-not $NoSkill) {
  Step 'Agent skill'
  $src = Join-Path $Repo 'skills\paper-video-pipeline'
  $text = [IO.File]::ReadAllText((Join-Path $src 'SKILL.md'), [Text.Encoding]::UTF8).Replace('{{REPO_DIR}}', ($Repo -replace '\\', '/'))
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  $done = 0
  foreach ($agent in '.claude', '.codex', '.agents', '.gemini') {
    $root = Join-Path $SkillHome $agent
    if (-not (Test-Path $root)) { continue }
    $dst = Join-Path $root 'skills\paper-video-pipeline'
    $marker = Join-Path $dst '.installed-by-setup'
    if ((Test-Path $dst) -and -not (Test-Path $marker) -and -not $ForceSkill) {
      Warn "$dst already exists and was not made by this setup; left untouched (rerun with -ForceSkill to overwrite)"
      continue
    }
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    Get-ChildItem $src | Where-Object { $_.Name -ne 'SKILL.md' } | Copy-Item -Destination $dst -Recurse -Force
    [IO.File]::WriteAllText((Join-Path $dst 'SKILL.md'), $text, $utf8)
    [IO.File]::WriteAllText($marker, $Repo, $utf8)
    Ok "-> $dst"
    $done++
  }
  if ($done -eq 0) { Warn 'no agent folder found (~/.claude, ~/.codex, ~/.agents, ~/.gemini); install an agent first or copy skills/paper-video-pipeline yourself' }
}

Step 'Smoke test'
Push-Location (Join-Path $Repo 'template')
try {
  Py ..\tools\fake_timeline.py narration.example.json src\film\data\vo.ts
  Py ..\tools\check_anchors.py src\film src\film\data\vo.ts
  & npx.cmd tsc --noEmit
  if ($LASTEXITCODE -ne 0) { Fail 'type check failed' }
} finally { Pop-Location }
Ok 'timeline, anchors and type check pass'

Write-Host ""
if ($Warnings.Count) { Write-Host "Done with $($Warnings.Count) warning(s) above." -ForegroundColor Yellow } else { Write-Host 'All set.' -ForegroundColor Green }
Write-Host @"

Next:
  cd template
  npx remotion studio                                   # preview the example film
  python -X utf8 ..\tools\tts_edge.py narration.example.json out\vo      # voice it (free Edge TTS)
  python -X utf8 ..\tools\assemble_natural.py narration.example.json out\vo public\audio\vo.wav src\film\data\vo.ts
Chinese: use narration.zh.example.json. Full steps: README.md. In Claude Code / Codex, just ask for a paper video.
"@
