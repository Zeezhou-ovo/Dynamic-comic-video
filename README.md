# Dynamic-comic-video

把一段故事、剧本或角色设定，做成带配音、字幕和局部表演的动态漫画短片（漫剧 / motion comic）。

这是一个**通用的 AI skill**，不绑定任何 AI 产品。它由两部分组成：一份写给 AI 看的制作规则 [SKILL.md](SKILL.md)，和一组在你本机运行的 Python / Node 脚本（校验、质量检查、Remotion 渲染）。任何能读文件、能执行命令的 AI 助手都可以按它跑完整个流程；只能聊天的 AI 也能用它来写分镜、数据文件和生图提示词。

## 能做什么

**从内容到分镜。** 先确定受众、平台、开头钩子和结尾收获，再拆出叙事节拍和逐镜分镜；角色参考只锁身份、服装和比例，每一镜按剧情重新设计姿势和构图，不反复粘贴同一张立绘。

**生图提示词。** 把角色参考、每镜 master 和分层需求编译成带追溯字段的提示词，交给你环境里可用的生图工具。仓库本身不内置任何云端生成服务。

**固定机位的局部表演。** 嘴型按实际配音的音量在闭 / 半开 / 全开之间切换，也可以手工指定；眨眼、手势姿态切换、表情替换（比如惊讶眉眼）都按事件触发，动作有准备、动作、回稳，静止也算表演，不做机械的漂浮和摇摆。

**道具运动。** 从 master 抠出的道具可以连同骑在上面的角色一起摇动或前倾（比如摇木马），角色身上的嘴、眼补丁会跟着一起动，后方背景需要补全。

**镜头与导演（可选）。** 逐镜启用推拉摇移和五层 2.5D 视差；用对话导演文件安排谁说话、谁反应、在哪里停顿、哪句是笑点。同一份对白和素材还能切换搞笑对话、知识讲解、动态漫画、故事动画四种模式。

**声音。** 字幕、嘴型、动作和切镜都以实测配音为准；支持音效文件、全片底噪，自带一个生成原创音效（木头吱呀声、室内底噪、轻弹音）的脚本；预览渲染后自动把整体响度调到约 −14 LUFS。

**漫画符号和关键词字幕。** 汗滴、无语线、问号、短震动、彩色关键词等都能画，但**默认不加**，只有你明确要求时才会写进项目。字幕默认白字黑描边。

**检查与交付。** 预览前有质量闸门（时间轴、嘴型、台词前后的空白、笑点后的停顿、正反打背景重复等）；预览时导出每镜首、中、末帧供人工复核；交付闸门用 ffprobe 检查成片的尺寸、帧率和时长，并报告响度。自动检查只覆盖能计算的部分，画面质量仍需要人看。

## 环境要求

Python 3.10 以上，Node.js 18 以上（npm 8 以上），以及 ffmpeg / ffprobe。Python 依赖见 `requirements.txt`。

## 安装

```sh
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
cd Dynamic-comic-video
python -m pip install -r requirements.txt
bash scripts/setup.sh
```

Windows PowerShell 用 `.\scripts\setup.ps1`。不带参数时，安装脚本只检查环境，并告诉你 SKILL.md 的位置。

如果你的 AI 工具会从某个 skill 目录自动加载 skill，可以把它复制过去，目录名用 `dynamic-comic-video`：

```sh
bash scripts/setup.sh --dest <你的 AI 工具读取的 skill 目录>/dynamic-comic-video
```

`--dest` 可以写多次，一次装进多个工具。各工具的 skill 目录位置以它们自己的文档为准。

## 在 AI 里使用

**会自动加载 skill 的 AI 工具：** 装好后直接说需求就行，比如“用 dynamic-comic-video 把这段故事做成 15 秒动态漫画，先出分镜给我看”。

**能读文件、能跑命令，但不会自动加载 skill 的 AI 助手：** 在这个仓库目录里打开它，或者告诉它“先读 `<仓库路径>/SKILL.md`，按里面的规则做”。仓库根目录的 [AGENTS.md](AGENTS.md) 也写了同样的入口说明，很多 AI 编程工具会自动读取这个文件。

**只能聊天的 AI：** 把 SKILL.md 和相关的 `references/` 文档发给它，让它写分镜、JSON 数据文件和生图提示词；下面的命令由你自己在电脑上运行。

不论用哪种 AI，你的视频项目（故事、角色图、配音、成片）都放在本仓库之外的独立文件夹里。

## 常用命令

```sh
python scripts/pipeline.py validate <项目> --assets        # 校验数据和素材
python scripts/quality_gate.py <项目>                       # 预览前的质量闸门
python scripts/make_sfx.py <项目>                           # 生成原创音效到 <项目>/audio/sfx/
python scripts/preview.py <项目> --renderer <项目外的渲染目录> --npm-install   # 渲染预览 MP4 和复核帧
python scripts/project_state.py review <项目> --approve     # 看过复核帧后记录批准
python scripts/deliver.py <项目>                            # 交付闸门
python scripts/doctor.py                                    # 检查本机环境
```

想先看看流程是否跑得通，可以用合成测试素材生成一个示例项目再渲染：

```sh
python scripts/make_performance_fixture.py ../performance-demo
python scripts/preview.py ../performance-demo --renderer ../performance-demo-renderer --npm-install
```

无法自动下载 Remotion 所需浏览器时，见 [运行指南](references/runbook.md) 的排错部分。

## 文档

制作规则入口是 [SKILL.md](SKILL.md)。数据文件说明见 [数据契约](references/contracts.md)；嘴型、表情、道具运动、音效和漫画符号见 [漫画表演运行时](references/performance-runtime.md)；镜头与视差见 [Camera 与 Parallax 运行时](references/camera-parallax-runtime.md)；对话导演见 [Dialogue & Performance Director](references/dialogue-performance-director.md)；模式与模板见 [Mode + Template 使用说明](docs/phase5-mode-template.md)；完整运行步骤见 [运行指南](references/runbook.md)。

## 版本

当前工作流版本是 V1.0。新项目使用 `motion_plan` 0.4，其余数据文件使用 0.1；旧的 0.1–0.3 项目按原有含义继续可用。变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## 相关仓库

用代码逐帧绘制画面的路线（p5.js / p5.brush、浏览器逐帧截取和 FFmpeg）在独立仓库 [code-painted-video](https://github.com/zeezhouovo-creator/code-painted-video) 维护，两条路线的数据格式和渲染流程各自独立。

## 参与修改

从 `main` 创建分支并提交 Pull Request，提交前按 [贡献指南](CONTRIBUTING.md) 运行测试。许可证为 [MIT](LICENSE)。
