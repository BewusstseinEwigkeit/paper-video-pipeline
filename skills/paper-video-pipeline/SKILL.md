---
name: paper-video-pipeline
description: 论文与项目展示视频流水线（Remotion 画面挂在旁白的词上）。从旁白文案出发，配音（默认免费 Edge TTS，中英文都支持）、逐词时间轴、画面、混音、质检、字幕、压缩、发布。用于做论文介绍视频、项目展示视频、答辩视频，按审稿或导师意见改片，或者把一篇论文讲成几分钟的片子。
---

# 论文展示视频流水线

## 先找到仓库

脚本和模板在 paper-video-pipeline 仓库里，下文用 `$PVP` 指仓库根目录。按顺序找：

1. 本 skill 目录往上两级（`<skill 目录>/../..`）有 `tools/` 和 `template/`，那里就是仓库根。用 Claude Code 插件安装时是这种情况。
2. 一键配置脚本写进来的路径：`{{REPO_DIR}}`。如果这里还是花括号占位符，说明不是用 setup 装的，跳过这一条。
3. 以上都没有，就 `git clone https://github.com/BewusstseinEwigkeit/paper-video-pipeline`，在仓库根运行 `powershell -ExecutionPolicy Bypass -File setup.ps1`（Windows）或 `bash setup.sh`（macOS、Linux）。

开工前按需读 `$PVP/docs/`：`00-思路与工作流.md`（创作原则）、`01-流水线.md`（每一步的细节）、`02-字体与动效规范.md`、`03-踩坑记录.md`。

## 新片子怎么起

1. 把 `$PVP/template` 整个复制到新的工程目录，在那里 `npm install`。不要直接改仓库里的模板。
2. 写 `narration.json`。英文参考 `narration.example.json`，中文参考 `narration.zh.example.json`（`"lang": "zh"`）。
3. 在新工程目录里按下表执行，脚本都用 `$PVP/tools/` 里的。

| 阶段 | 命令 | 门禁 |
|---|---|---|
| 1 占位排画面 | `python -X utf8 $PVP/tools/fake_timeline.py narration.json src/film/data/vo.ts` | 文案没定稿也能先排画面 |
| 2 配音 | `python -X utf8 $PVP/tools/tts_edge.py narration.json out/vo` | 默认 Edge TTS，免费、无需密钥；可只重配某一章（末尾加章节键）。要 Gemini 音色用 `tts_gemini.py`（需 gcloud） |
| 3 复听 | `python -X utf8 $PVP/tools/verify_voice.py out/vo` | 中型 Whisper 复听专名、缩写和数字的读音 |
| 4 词轴 | `python -X utf8 $PVP/tools/assemble_natural.py narration.json out/vo public/audio/vo.wav src/film/data/vo.ts` | 保留自然停顿，逐词计时 |
| 5 混音 | `python -X utf8 $PVP/tools/mix_all.py public/audio/vo.wav music.mp3 public/audio/final.wav` | 人声前 0.95 秒压低配乐；在 `src/film/config.ts` 设 `audio: "audio/final.wav"` |
| 6 锚点与渲染 | `python -X utf8 $PVP/tools/check_anchors.py src/film src/film/data/vo.ts`，再 `python -X utf8 $PVP/tools/gpu_lock_render.py --cwd . -- render Full out/full.mp4 --scale=1.5 --concurrency=4 --codec=h264 --crf=16` | BAD = 0、WARN = 0 才渲染 |
| 7 质检与交付 | `qa_video_audit.py`、`export_subs.py`、`web_encode.py`（用法见 README） | 看联系表；压到附件上限以内 |

画面里的时间一律写成 `at("行 id", "旁白里的词")`，不写秒数。中文旁白按字计时，锚点可以挂在旁白里出现的英文术语和数字上，比如 `at("r1", "48.2")`。

## 核心原则

1. **论文主线优先**：以论文框架图为全片地图，点出核心模块名；重点讲背景、问题和实验证据，少讲实现细节；时长按要求控制，常见是 4 分钟以内；片尾不讲自己的缺点。
2. **画面挂在词上**：所有出入场和强调都用 `at()` 挂在逐词时间轴上，改文案、重配音后画面自动对齐。
3. **分工与隔离**：主控读论文、定分镜、写任务书；写代码的模型按章节目录隔离并行；视觉和数字由没参与写代码的另一家模型对照抽帧联系表审查。
4. **数字与原图红线**：上屏的指标、曲线和表号逐条核对论文正文；不编造过渡数值；不经作者同意不删核心框架图；画面里不放防御性小字。
5. **分级渲染**：迭代只看静帧和 10 到 40 秒带声样片，叙事和视觉定稿后再渲 1080p 全片。

## 派活任务书最小结构

1. 工作目录边界：只许改指定章节的文件。
2. 只读文件：`vo.wav`、`final.wav`、`src/film/data/vo.ts`。
3. 数字与原图：附核对过的指标清单、必须出现的原图路径、匿名要求。
4. 验收命令：退出前跑通 `npx tsc --noEmit`、`check_anchors.py`、关键静帧和联系表。

## 开工前要备好的材料

1. 论文 PDF 和高清原图（框架图、定性图、结果图）。
2. 定稿旁白。
3. 关键实验的回放视频（有的话）。
4. 时长上限和匿名要求。
