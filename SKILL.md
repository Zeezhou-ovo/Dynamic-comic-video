---
name: dynamic-comic-video
description: Create and revise sequential motion-comic videos from stories, scripts, character references, or independent panels. Use for dynamic comics, motion comics, 动态漫画, or 漫剧 with consistent characters, fixed-camera local acting, timed audio/subtitles, and Remotion MP4 output. Not for generic slideshows, full frame-by-frame animation, or phoneme lip sync.
---

# Dynamic Comic Video — V1.0 workflow

将用户内容制作成连续分镜式动态漫画：剧情决定分镜，事件触发人物表演，实际声音决定时间，硬切推进叙事。当前对外版本是 V1.0；历史文档中的 V0.4 只表示这套工作流早期的执行闭环，已经纳入 V1.0，不是另一套运行模式或产品版本。

## 入口与按需加载

先读取 [总控与恢复规则](references/v10-control-system.md)，判断本次是新建、继续还是局部修改。只加载当前阶段对应的文档，不一次读完全部 references。用户只请求分镜、提示词或局部修改时，到该交付物完成为止，不自动扩展为整片制作。

| 当前任务 | 读取 | 本阶段结果 |
| --- | --- | --- |
| 新建、素材入口或关键信息缺失 | [制作向导](references/production-wizard.md)、[内容目录](references/content-intake.md)、[内容策划](references/content-strategy.md) | 独立项目目录、brief、内容策略与明确假设 |
| 恢复已有项目 | [项目状态机](references/project-state.md) | inspect 先做 Schema 检查，再结合素材指纹、返工台账和视觉复核清单判断下一步 |
| 建立或复核角色 | [角色一致性](references/character-consistency.md) | characters 与核对过的身份参考；无人物允许空列表 |
| 生成或改写分镜 | [分镜主规则](references/storyboard-director.md)、[连续分镜](references/sequential-comic.md) | 场景空间、Narrative Beats、shots 与17项逐镜审阅稿 |
| 生成 master 与分层 | [生图规范](references/image-generation-spec.md)、[分层协议](references/layer-protocol.md)；简化条漫画风读取 [风格预设](references/simple-comic-style.md)，经济档另读 [生图档位](references/comic-generation-economy.md) | 带追溯字段的角色参考、核对过的 master、对齐图层和补全背景 |
| 设计人物动作 | [自然度](references/motion-naturalness.md)、[有限动画](references/limited-animation.md) | 有原因、可复核的局部动作与静止阶段 |
| 配音、字幕、嘴型及节奏 | [音频时间轴](references/audio-timeline.md) | 实测音频驱动的统一逐镜时间轴 |
| 强调字幕、漫画符号、音效或音乐 | [漫画演出](references/comic-performance.md) | 同一时间轴中的必要视听事件 |
| 校验、预览与交付 | [质量闸门](references/quality-gate.md)、[运行指南](references/runbook.md) | QC 报告、可播放 MP4、视觉复核记录、交付报告 |

写 JSON 前读取 [契约说明](references/contracts.md) 和对应 `schemas/*.schema.json`。新项目使用 `motion_plan.version: "0.3"`，其余三份制作合同为 `"0.1"`；旧 0.2 动作按有限动画协议兼容，不因 Skill 升级批量改版本。

面向真实观众的视频先完成 [短视频内容策划层](references/content-strategy.md)：明确受众、平台、目标、前 1–2 秒钩子、一个核心承诺、结尾收获和可选 CTA，再把内容拆成 Narrative Beats 与 shots。没有内容策略的工程测试可以继续使用最小 brief，但不能把测试素材当成成片内容。

条件模块：选择纸片拼贴时读 [画风预设](references/paper-collage-style.md)，选择简化搞笑条漫画风时读 [风格预设](references/simple-comic-style.md)；明确固定机位微动作时读 [微动作模式](references/fixed-camera-micro.md)；要求知识卡、总结卡或 CTA 时读 [收束卡](references/outro-card.md)。发布验收才读 [制作闭环与验收](references/v04-production.md)，规划能力扩展才读 [后续优化路线](references/v05-roadmap.md)。

## 全程保持的创作约束

- 保留原文的题材、地域、时代、关系、因果、事实边界与情绪。视觉语言由用户或 brief 决定，示例不是题材限制。关键设定无法可靠判断才问，其余合理假设写入 brief。
- Character Reference 只锁身份、服装、比例与辨识锚点，不锁姿势、表情、景别和构图。新绘镜头按剧情设计表演，不能反复粘贴固定立绘。
- 先提取 Narrative Beats，再设计 Shots。跨镜维持空间连续，背景随独立机位重新构图；不能只裁切放大同一图冒充新镜头。已有分镜的复用边界由总控规则统一定义。
- 先完整 master，再以它为唯一对齐基准提取或重建图层；保持画布、坐标、透视、尺度与光向，补全被遮挡背景。缺层就记录缺项，不降级成整图推拉。
- 默认 `performance.mode: sequential-comic`，镜内固定机位，禁用镜头推拉、平移、旋转、缩放及视差。局部动作需要事件原因和准备→动作→停顿/回稳；静止也是有效表演。大型姿势变化优先拆镜，禁止周期浮动、摇摆和机械呼吸。
- 实际配音先于最终字幕、嘴型、动作触发与 CUT 定时。没有音频时可以草拟时间，但不能报告为已同步；无对白作品不强加配音或嘴型。
- 默认新生图档位为 `comic-economy`，用户已有选择优先。知识卡、总结卡、CTA、特效和背景音乐只按创作需求启用。

## 执行与验证

从本文件定位绝对技能目录，保留独立项目与 renderer 的绝对路径。文档中的 `scripts/...` 均相对技能目录，`<project>` 指用户项目；路径含空格时加引号。优先使用已安装环境的 Python，不假定当前目录就是技能根目录。

1. 完成当前阶段的数据与资产，再运行 `scripts/pipeline.py validate <project>` 和 `compile <project>`；compile 整理导演决策，不替代剧情设计或图像生成。
2. 核对角色、master、图层及实际运动范围后才填写 `ready`、`review` 或 `performance.reviewed`。fixture 只用于管线测试，不得改标签冒充正式素材。
3. 预览可用 `scripts/preview.py <project> --renderer <external-renderer>`；单镜头可追加 `--shot <shot_id>`，输出默认为 `preview_<shot_id>.mp4`。流程执行素材校验、质量闸门安全修正、再校验、编译、prepare 和 Remotion 渲染；首次安装 renderer 依赖才追加 `--npm-install`。每次预览还会把首/中/末帧复制到 `<project>/visual-review/`，并写入 `visual_review.json`。
4. Critical/Major 问题修复后才进入预览。自动闸门只验证可计算条件；打开 `visual_review.json` 中的图片，查看逐镜接触表、关键帧及中间帧、切点两侧，检查身份、接缝、接触、遮挡、字幕与节奏。按叙事需要保留反应时间；实际查看后使用 `python scripts/project_state.py review <project> --approve`，发现问题使用 `--reject --note`。复核清单绑定当前源文件和媒体指纹，修改输入后必须重新预览。
5. 多镜头返工使用 `python scripts/project_state.py revision add <project> --text "..." --shot <shot_id>` 记录；处理后更新为 `resolved`。需要只重做变更镜头时使用 `scripts/preview.py <project> --renderer <external-renderer> --incremental`，它只更新指纹变化或缓存缺失的镜头。
6. 新机器或 renderer 变更后先运行 `python scripts/doctor.py`；它只检查本地环境，不安装依赖、不上传项目和密钥。
7. 视觉复核批准且返工台账清空后运行 `python scripts/deliver.py <project>`；交付闸门会用本地 `ffprobe` 验证 MP4 的可播放性、尺寸、帧率和时长，并把结果写入 `delivery_report.json`。报告为 `FAIL` 时按 `blocking_issues` 修复。
8. 选择 `style_preset: "simple-comic"` 做图片优先试片时，先用 `scripts/generate_simple_comic_motion_assets.py <project>` 生成明确标注的眨眼和源图嘴型变体，再用 `scripts/preview.py <project> --simple-comic` 渲染。没有变体时仍可出静态预览，但不能声称包含眼睛或嘴部表演；未经对齐审核的通用嘴型不得覆盖 master。
5. 重复检查包括相邻 pose_tag、连续三镜景别/角度/构图标签和人物 PNG 哈希。标签或哈希不同不证明画面不同；合理重复写明 `repetition_exception`，不能改标签掩盖固定立绘复用。
6. 交付说明实际完成阶段、测试/正式素材状态、时长、尺寸、输出绝对路径与剩余问题。只通过校验不能声称已渲染；存在 MP4 也不等于完成视觉验收。

缺少图像、配音或渲染能力时，保存已完成文件，列出具体缺项和恢复入口，继续完成不依赖缺项的工作。不得虚构资源、复核或成片成功。

## 工具、隐私与保留

使用当前环境可用且已获授权的图像/音频工具，读取相应技能说明；本项目不内置云端生成 API。能力边界是局部关键帧、对齐姿态切换与简单音量驱动嘴型，不承诺自动抠图、骨骼绑定、精确音素口型或完整逐帧动画。

用户原文、参考、JSON、配音、master、图层、预览和 MP4 保存在仓库之外的独立项目目录，renderer 位于项目之外。保留源素材和恢复所需中间文件；只在用户要求清理时删除已明确范围的临时文件，不因交付完成自动删除。

API Key、Token、密码不得写入项目 JSON、提示词、renderer/public、日志、交付包或上传网络。需要凭据时优先从本地环境变量或加密配置读取，且遵守用户仅限本地使用的约束。用户粘贴明文密钥时提示风险并指导改用本地配置，不用该明文密钥请求网络。配置帮助只询问本地文件路径，提供用户本地执行的命令；不兼容上述限制的适配器明确说明。
