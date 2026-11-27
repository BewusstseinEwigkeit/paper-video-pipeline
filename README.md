# paper-video-pipeline

论文展示视频流水线：从旁白文案出发，配音、逐词时间轴、Remotion 画面、混音、质检、字幕、压缩、发布，每一步都有对应的脚本。画面用“旁白里的某个词”定位时间，不写秒数，所以改文案、换配音时画面能自动跟上。配音默认用免费的 Edge TTS，英文和中文都支持。

## 一键配置

```powershell
git clone https://github.com/BewusstseinEwigkeit/paper-video-pipeline
cd paper-video-pipeline
powershell -ExecutionPolicy Bypass -File setup.ps1      # Windows
```

```bash
bash setup.sh                                           # macOS / Linux
```

脚本会做这些事：检查 Python 3.10+、Node 20+、ffmpeg，缺了就用 winget（Windows）或 Homebrew（macOS）装上；把 `requirements.txt` 装进当前的 Python（conda、venv 环境都认，macOS / Linux 不在虚拟环境里时装进 `.venv`）；在 `template/` 里 `npm install`；下载计时用的 Whisper 小模型（约 0.5 GB）；给 Claude Code、Codex、Gemini CLI、Antigravity 装上 skill；最后跑一遍冒烟测试。可选参数见脚本开头的注释。

国内网络下载 Whisper 模型失败时，先设 `HF_ENDPOINT=https://hf-mirror.com` 再运行一次。

## 只装 skill

- **Claude Code 插件**（不用克隆，脚本随插件一起装好）：

  ```
  /plugin install paper-video-pipeline --marketplace BewusstseinEwigkeit/paper-video-pipeline
  ```

  旧版本 Claude Code 分两步：`/plugin marketplace add BewusstseinEwigkeit/paper-video-pipeline`，再 `/plugin install paper-video-pipeline@paper-video-pipeline`。Python、Node、ffmpeg 这些依赖仍要装，跑一次 `setup.ps1` / `setup.sh` 最省事。
- **其他 agent**：`setup.ps1` / `setup.sh` 会把 `skills/paper-video-pipeline` 复制到 `~/.claude/skills`、`~/.codex/skills`、`~/.agents/skills`、`~/.gemini/skills` 中已存在的那些目录，并写入仓库路径。

装好以后直接对 agent 说“用 paper-video-pipeline 给这篇论文做一个 4 分钟的展示视频”就行。

## 快速开始

```powershell
cd template
npx remotion studio                                                                  # 预览示例片
python -X utf8 ..\tools\fake_timeline.py narration.example.json src\film\data\vo.ts   # 没配音时先用占位时间轴排画面
python -X utf8 ..\tools\check_anchors.py src\film src\film\data\vo.ts
```

配音以后（下面以 `narration.json` 代表你的文案，可从 `narration.example.json` 或 `narration.zh.example.json` 复制）：

```powershell
python -X utf8 ..\tools\tts_edge.py narration.json out\vo                 # Edge TTS，按章节整段合成
python -X utf8 ..\tools\verify_voice.py out\vo                            # 中型 Whisper 复听读音
python -X utf8 ..\tools\assemble_natural.py narration.json out\vo public\audio\vo.wav src\film\data\vo.ts
python -X utf8 ..\tools\mix_all.py public\audio\vo.wav music.mp3 public\audio\final.wav
# 在 src/film/config.ts 里设置 audio: "audio/final.wav"
python -X utf8 ..\tools\check_anchors.py src\film src\film\data\vo.ts
python -X utf8 ..\tools\gpu_lock_render.py --cwd . -- render Full out\full.mp4 --scale=1.5 --concurrency=4 --codec=h264 --crf=16
python -X utf8 ..\tools\qa_video_audit.py --input out\full.mp4 --json out\qa.json --sheet out\qa.jpg
python -X utf8 ..\tools\export_subs.py src\film\data\vo.ts out\film
python -X utf8 ..\tools\web_encode.py out\full.mp4 out\film_web.mp4 95
```

做自己的片子时，把 `template/` 整个复制出去再改，脚本仍从本仓库的 `tools/` 调用。

## 中文旁白

在 `narration.json` 里写 `"lang": "zh"`，示例见 `template/narration.zh.example.json`。中文按字计时，标点并到前一个字上，英文术语和数字保持整体，所以画面锚点可以挂在旁白里出现的术语和数字上（`at("b2", "classify")`、`at("r1", "48.2")`）。字幕按中文宽度断行，中英文之间自动留空格。默认音色 `zh-CN-YunyangNeural`，换音色改 `"tts": {"voice": ...}`，全部音色用 `python -m edge_tts --list-voices` 查。

## 换 Gemini 音色

Edge TTS 不读导演提示。想要能按章节调语气的音色，用 `tools/tts_gemini.py`，设置写在 `"tts_gemini"`（见示例文件）。它走 Google Cloud Text-to-Speech，需要自己的 GCP 项目、`gcloud auth login`，并在项目里开通 Text-to-Speech API。两个引擎输出同样的 `_sec_*.wav`，后面的步骤不变。

## 目录

| 路径 | 内容 |
|---|---|
| `setup.ps1` / `setup.sh` | 一键配置 |
| `skills/paper-video-pipeline/SKILL.md` | agent skill |
| `.claude-plugin/` | Claude Code 插件清单 |
| `docs/00-思路与工作流.md` | 创作思路、叙事主线与多模型协作流程 |
| `docs/01-流水线.md` | 每一步做什么、怎么跑、为什么这样做 |
| `docs/02-字体与动效规范.md` | 字体、配色语义、缓动和时长、组件清单 |
| `docs/03-踩坑记录.md` | 时间锚点、音频、画面、内容、交付五类问题及现在的做法 |
| `tools/` | Python 工具链（见下表） |
| `template/` | 最小 Remotion 工程：字幕、章节标记、动效原语，加四个示例场景；英文和中文示例文案 |
| `site/publish_ssh.py` | 用 ssh 上传静态站点，并从公网地址校验 |

| 工具 | 作用 |
|---|---|
| `tts_edge.py` | 默认配音：Edge TTS，每章一次请求整段合成，可以只重合成某一章 |
| `tts_gemini.py` | 可选配音：Gemini TTS，能读每章的导演提示 |
| `verify_voice.py` | 用中型 Whisper 复听，检查读音 |
| `assemble_natural.py` | 整段录音上时间轴，截短过长停顿，生成 `vo.wav` 和逐词时间轴 `vo.ts` |
| `fake_timeline.py` | 不配音，先生成占位时间轴来排画面 |
| `mix_all.py` | 用提前量包络压低配乐；配乐太短时自动放慢 |
| `check_anchors.py` | 检查画面里所有 `at()` 锚点，并报出写死的秒数 |
| `gpu_lock_render.py` | 渲染锁，同一时间只跑一个渲染任务，并记录日志 |
| `qa_video_audit.py` | 检查分辨率、黑帧、冻结、响度和真峰值，并出联系表 |
| `export_subs.py` | 输出 SRT、VTT 和逐词 JSON |
| `web_encode.py` | 压到附件上限以内（默认 95 MB） |
| `textutil.py` | 各工具共用的分词、计时语言设置 |

## 依赖

- Node 20 以上；Remotion 4.0.541，版本锁在 `template/package-lock.json`。
- Python 3.10 以上，`numpy`、`faster-whisper`、`edge-tts`（`requirements.txt`）；系统里要有 `ffmpeg` 和 `ffprobe`。
- Edge TTS 需要能连上 `speech.platform.bing.com`；Whisper 模型第一次用时从 Hugging Face 下载。
- 3D 场景要另外装 `three` 和 `@remotion/three`，并保持 `remotion.config.ts` 里的 ANGLE 设置。

## 许可

代码 MIT（见 `LICENSE`）。`template/public/fonts/` 里的字体是 SIL Open Font License，许可证和字体放在一起。
