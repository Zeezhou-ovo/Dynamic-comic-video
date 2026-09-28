# Dynamic-comic-video

这是一个关于制作动态漫画视频的 Agent Skill 尝试。它用于探索如何把故事、角色、漫画分镜、局部人物动作、配音字幕和 Remotion 输出组织成连续分镜式动态漫画视频。

项目目前处于持续试验和迭代阶段，欢迎项目组成员通过 GitHub 共同完善。真实故事、角色图和成片留在各自本地。

## 安装方式

项目采用一体化安装：一次安装同时得到 Agent Skill、Python 校验环境和 Remotion MP4 渲染器。团队成员不需要分别安装 Skill 和 npm 渲染项目。

Windows：

```powershell
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
Set-Location Dynamic-comic-video
.\scripts\setup.ps1
```

macOS/Linux：

```bash
git clone https://github.com/zeezhouovo-creator/Dynamic-comic-video.git
cd Dynamic-comic-video
bash scripts/setup.sh
```

安装脚本会把 Skill 放到 Codex 的 Skill 目录，在本地创建 Python 虚拟环境，并在 `assets/remotion` 中安装 npm 依赖。安装完成后，用户可以直接用 Codex 制作动态漫画，也可以进入独立项目执行校验、预览和 MP4 渲染。

每个故事、角色图片、配音、渲染项目和成片都保存在仓库之外。不要把 `node_modules`、`.venv`、API Key 或用户内容提交到 GitHub。更新时在仓库目录执行 `git pull`，再重新运行对应的安装脚本。

## 协作方式

日常修改请从 `main` 创建分支并提交 Pull Request。提交前运行 [贡献指南](CONTRIBUTING.md) 中的测试。版本变化记录在 [CHANGELOG.md](CHANGELOG.md)，稳定版本使用 Git tag 标记。

## V1.0 workflow

默认制作固定构图的连续分镜式动态漫画。当前对外版本是 V1.0，包含项目状态识别、入口分流、最小提问、统一 Scene 路由、用户反馈定位和局部返工控制，并内置已经验证的固定机位执行闭环。旧文档中的 V0.4 是这套闭环的历史开发编号，不是与 V1.0 并列的另一版本。需要恢复或交接项目时可使用 [项目状态机](references/project-state.md)，用 `inspect` 只读判断下一阶段；它还会检查素材报告的缺失/指纹变更和视觉复核清单，避免旧 MP4 或未复核帧掩盖返工项。预览完成后用 `project_state.py review --approve` 或 `--reject --note` 记录人工结论，输入变更会自动使旧复核失效。完整总控规则见 [V1.0 总控系统](references/v10-control-system.md)，执行闭环见 [制作闭环与验收](references/v04-production.md)。V1.0 仍不是精确音素口型、自动抠图或无人审核的全自动成片。

`inspect` 会报告四份生产合同的 Schema 错误和具体字段路径；`revision add/update` 保存返工台账。多镜头项目可使用 `preview.py --incremental` 按素材指纹复用未变化镜头，`doctor.py` 用于检查本地 Python、Node、npm 和 Remotion 环境。交付前运行 `python scripts/deliver.py <独立项目目录>`，它会生成 `delivery_report.json`，统一检查合同、质量报告、视觉复核新鲜度、未关闭返工项，以及本机 `ffprobe` 读取的 MP4 可播放性、尺寸、帧率和时长。

分镜生成统一使用 [分镜生成主规则](references/storyboard-director.md)：同一空间连续、背景构图按独立机位变化、角色身份连续、说话与倾听均有表演、切镜有因果，并输出17项逐镜审阅稿。旧五项简表已替换。

真实发布内容先读取 [短视频内容策划层](references/content-strategy.md)，在 brief 中明确受众、平台、钩子、核心承诺和结尾收获，再进入角色与分镜制作。这样可以先解决“观众为什么继续看”，再决定画面如何动。

生图阶段遵循 [生图规范与提示词合同](references/image-generation-spec.md)：角色参考只锁身份，master 承担当镜构图，图层从同一 master 提取；`pipeline compile` 会给提示词写入版本、镜头 ID、参考图用途和负面约束，便于跨模型复现与返工。

参考简化搞笑条漫画面时使用 `style_preset: "simple-comic"`：粗线、平涂、夸张表情、简化背景，并在画面下方预留字幕区；对白不生成气泡，统一由后期字幕层添加。

已有能力：

- `production_brief.json`、`characters.json`、`storyboard.json`、`motion_plan.json` 的严格 Schema 与跨文件检查。
- Narrative Beats 先于 Shots 的分镜工作流。
- “完整 master → 对齐提取/重建图层”的图层协议，包含背景补全要求。
- pose、景别、角度、构图标签的重复预警，以及重复人物 PNG 的阻断检查。
- Remotion 局部部件平移、关节旋转、透明度关键帧，以及对齐姿态图片切换；硬切是默认镜头衔接，旧视差只作为兼容路径，不用于新 sequential-comic 镜头。
- 动作意图与静止理由校验，阻止纯推拉冒充角色表演。真实动作质量仍须目视复核。
- 支持本地配音、字幕和音量驱动的简单嘴部开合；不包含精确音素口型、骨骼绑定或完整逐帧动画。
- 提供 `comic-economy` 生图档位：以角色参考和动作可读性为先，背景适度简化，适合连续分镜批量生产。
- 知识卡、总结卡和 CTA 是按 brief 启用的可选收束镜头，不会自动追加到每个项目。

新制作使用 `motion_plan` 0.3，其他合同保持 0.1；这些是 V1.0 工作流的数据合同版本，不是 Skill 发布版本。旧的 0.2 有限动画入口仍可读取，迁移规则见 [有限动画协议](references/limited-animation.md)。library 示例保留为回归测试；运行 `python scripts/make_acting_fixture.py ../acting-fixture` 生成明确标记为 legacy 0.2 的固定相机测试，正式项目应使用 0.3 合同。它验证执行能力，不代表正式美术质量。

## 快速验证

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m unittest discover -s scripts -p "test_*.py"
.\.venv\Scripts\python scripts\pipeline.py compile examples\library
.\.venv\Scripts\python scripts\make_fixture.py examples\library
.\.venv\Scripts\python scripts\pipeline.py prepare examples\library --renderer ..\manga-renderer
```

随后在 `../manga-renderer` 中运行：

```powershell
npm ci
npm run render
```

示例使用本地几何测试素材，验证数据、透明层、视差和 MP4 管线；它不是某种主题的成片。正式项目需要按 `SKILL.md`、`references/content-intake.md` 与 `references/layer-protocol.md` 在独立工作目录中生成并检查真实 master 和分层素材。

如果想把校验、质量闸门、Remotion 准备和 MP4 预览合成一次执行，可以使用一体化预览脚本：

```powershell
python scripts/preview.py <独立项目目录> --renderer <项目外的渲染目录>
```

它会先运行素材校验和质量闸门，再编译提示词、准备外部 renderer、执行 Remotion，并把结果复制为项目目录下的 `preview.mp4`，同时生成 `visual-review/` 首/中/末帧和 `visual_review.json`。只预览一个镜头时追加 `--shot shot_002`，输出为 `preview_shot_002.mp4`。首次在该 renderer 目录安装依赖时追加 `--npm-install`。渲染目录必须在项目目录之外，以免把 `node_modules` 混入用户内容目录。

简化条漫画风的图片优先试片可以使用本地眼睛/嘴部变体恢复有限表演：

```powershell
python scripts/generate_simple_comic_motion_assets.py <独立项目目录>
python scripts/preview.py <独立项目目录> --simple-comic
```

这条路径保持 master 不变，只在明确的帧切换眨眼和源图嘴型；它不加入镜头推拉，也不把静态图片误报成动态表演。眨眼由本地 OpenCV 生成，嘴型变体默认保留 master 自带的自然表情，避免错位的通用椭圆覆盖人物原嘴型。项目素材和密钥不会上传。

视觉复核批准后运行 `python scripts/deliver.py <独立项目目录>`。只有 `delivery_report.json` 的 `status` 为 `PASS` 才算机器检查通过；`ffprobe` 必须在本机 PATH 中。该闸门只读本地文件，不安装依赖、不上传项目或密钥。

## 目录

```text
schemas/                 JSON Schema
examples/library/        一个可执行的三镜主题样例与测试素材
scripts/                 校验、提示词编译、渲染准备、测试
assets/remotion/         固定版本的 Remotion 模板
references/              数据契约、图层协议、运行和验证说明
SKILL.md                 Agent Skill 正式工作协议
```

## 长期维护方向

下一阶段优先补齐可检查的头部/手部/道具局部表演、声音与停顿质量、完整短话镜头覆盖和可追溯视觉复核。具体边界见 [后续优化路线](references/v05-roadmap.md)。任何扩展都应保持：用户原文不被改题材、角色参考不锁镜头姿势、master 是图层对齐的唯一视觉基准。

开发规范、运行细节和已验证边界见 [SKILL.md](SKILL.md) 与 [验证记录](references/validation.md)。
