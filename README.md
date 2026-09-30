# Dynamic-comic-video

这个仓库只维护 `dynamic-comic-video` Codex Skill：从故事和角色参考制作分镜、master 插画与对齐图层，设计局部表演和音频时间轴，再用 Remotion 预览与输出动态漫画。

## V1.0 workflow

新项目使用 `motion_plan` 0.4：默认沿用固定机位的 sequential-comic，逐镜显式启用时由 Remotion 执行确定性 Camera Motion 与五层 2.5D Parallax。旧 0.1–0.3 项目保留原有解释。运行数据和测试方法见 [Camera 与 Parallax 运行时](references/camera-parallax-runtime.md)。

## 安装

macOS/Linux：

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

安装后可在 Codex 中使用 `$dynamic-comic-video`。视频项目、角色素材、配音和成片放在本仓库之外。

代码逐帧绘制视频（p5.js／p5.brush、浏览器逐帧截取和 FFmpeg）由独立公开仓库 [code-painted-video](https://github.com/zeezhouovo-creator/code-painted-video) 维护，两条路线有各自的计划格式和渲染流程。

分镜与动态漫画制作规则见 [SKILL.md](SKILL.md)，安装后续步骤见 [运行指南](references/runbook.md)。日常修改从 `main` 创建分支并提交 Pull Request。
