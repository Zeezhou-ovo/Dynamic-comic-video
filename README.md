# Dynamic-comic-video

一个用**代码逐帧绘制**动态漫画视频的 Codex Skill。新项目默认用 p5.js＋p5.brush 在同一画布上绘制角色、场景、道具和效果；无头浏览器逐帧截取，再由 FFmpeg 合成 MP4。角色图片可以作为外观参考，但人物表演和场景变化应由绘制代码产生。

真实故事、角色参考、声音、帧文件和成片留在各自的项目目录，不提交到这个公共仓库。

## 安装 Skill

Windows：

```powershell
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
Set-Location Dynamic-comic-video
.\scripts\setup.ps1
```

macOS/Linux：

```sh
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
cd Dynamic-comic-video
bash scripts/setup.sh
```

安装脚本只复制 Skill 文件到 Codex 的 skills 目录；每个视频项目单独安装绘制和渲染依赖。已有用户更新仓库后重新运行安装脚本即可覆盖入口文档。不要把用户项目、`node_modules` 或密钥放进 Skill 目录。

## 开始一个视频项目

把 [逐帧绘制起始工程](assets/painted-frame-starter/README.md) 复制到仓库之外的目录，先在 `scene.js` 中写清画布、时长、角色与 `drawWorld(t)`，再运行：

```sh
npm install
npx playwright install chromium
node render.mjs --stills=0,2,4
node render.mjs --frames
node render.mjs --encode --audio=assets/audio.wav
```

音频是可选的；没有授权音轨时省略 `--audio`。模板的移动光点仅用来展示渲染接口，正式项目必须根据故事重新绘制人物、环境和动作。完整的创作与复核规则见 [SKILL.md](SKILL.md) 和 [代码逐帧绘制](references/painted-frame.md)。

## 制作要点

- 从 Narrative Beats 定义镜头与动作，再编写按绝对时间求值的绘制函数；同一个时间点应可重复生成同一帧。
- 角色与背景共享笔刷、色板、纸纹、空间和光照。检查脚底接触、手持道具、投影与前景遮挡，避免图片分层的拼贴感。
- 先看关键静帧，再看实际连续播放；修正动作的中间帧之后才输出完整 MP4。
- 交付代码、可重现命令、成片参数及剩余视觉限制。复杂角色可以风格化，但须如实说明与参考图的差异。

## 旧 Remotion 项目

此前的 `sequential-comic`、四份 JSON 合同、master／对齐图层协议和 Remotion 工具仍留在仓库中，供已有项目维护；它们不再是新项目默认流程。旧版说明见 [LEGACY_REMOTION.md](LEGACY_REMOTION.md)。不要将新代码绘制项目送入旧的 `pipeline.py prepare` 或 `preview.py`。

## 协作

日常修改从 `main` 创建分支并提交 Pull Request。变更记录在 [CHANGELOG.md](CHANGELOG.md)；用户私有素材与成片不进入公共仓库。
