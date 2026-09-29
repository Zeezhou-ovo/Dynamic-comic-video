# Dynamic-comic-video

这个仓库提供两条独立的视频制作 Skill。选用哪一条，取决于画面是由分层插画驱动，还是由代码逐帧绘制。

| Skill | 制作方式 | 适合 |
| --- | --- | --- |
| [`dynamic-comic-video`](SKILL.md) | 角色参考、完整 master、对齐图层、局部动作、配音字幕和 Remotion | 连续分镜式动态漫画；已有 `production_brief`／`motion_plan` 项目 |
| [`code-painted-video`](skills/code-painted-video/SKILL.md) | 同一绘制程序逐帧画角色与场景，无头浏览器截帧，FFmpeg 编码 | p5.js／p5.brush 风格的连续手绘动画；强调角色表演与镜头调度 |

两条路线有各自的入口、参考文档和制作合同。Remotion 路线使用四份 JSON 合同与 `scripts/preview.py`；逐帧绘制路线使用 `planVersion: 3` 的 `animation_plan` 与自己的渲染入口。不要将两种项目的计划、渲染命令互换。

## 安装

安装脚本会将两个 Skill 分别放入 Codex 的 skills 目录：

```sh
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
cd Dynamic-comic-video
bash scripts/setup.sh
```

Windows PowerShell：

```powershell
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
Set-Location Dynamic-comic-video
.\scripts\setup.ps1
```

安装后可明确指定 `$dynamic-comic-video` 或 `$code-painted-video`。仓库之外单独保存每个视频项目、角色参考、声音、帧和成片；不要把用户私有内容或密钥提交到这里。

## 两条路线的入口

- [分层动态漫画制作说明](SKILL.md)：从故事和角色参考制作 master 与对齐图层，安排局部表演和音频，用 Remotion 预览与输出。旧版完整说明见 [Remotion 工作流资料](LEGACY_REMOTION.md)。
- [代码逐帧绘制说明](skills/code-painted-video/SKILL.md)：先为每镜编写结构化动画计划，再绘制、截帧与编码。可复制 [起始工程](skills/code-painted-video/assets/painted-frame-starter/README.md) 到仓库外开始制作。

日常修改从 `main` 创建分支并提交 Pull Request。变更记录见 [CHANGELOG.md](CHANGELOG.md)。
