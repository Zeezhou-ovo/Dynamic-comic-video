# 数据契约与版本

新项目的 `production_brief.json`、`characters.json`、`storyboard.json` 使用 `version: "0.1"`，`motion_plan.json` 使用 `version: "0.4"`；四份文件共享 `project_id`，编码为 UTF-8。旧运动合同按 [有限动画协议](limited-animation.md) 兼容。Schema 不允许未声明字段。JSON Schema 负责结构；`pipeline.py` 负责跨文件引用和时间/素材一致性。0.4 的 Camera/Depth 字段见 [Camera 与 Parallax 运行时](camera-parallax-runtime.md)。

| 文件 | 所有者与主要字段 | 消费方 |
|---|---|---|
| production_brief.json | 原文、保留项、setting、visual_language、style_preset（含 simple-comic）、render_profile、tone、可选 content_strategy、format、assumptions | 所有阶段 |
| characters.json | identity 五类稳定特征；reference 路径、提示词、状态与 identity_only | 提示词编译、master QC |
| storyboard.json | beats 原文摘录/变化/情绪；shots 动作、表情、机位、构图、连续性、master、layers | 编译器、分层、QC |
| motion_plan.json | asset_mode、逐镜起始帧/时长、显式 camera、逐层 depth/局部动作/z、review | 素材 QC、Remotion |

Schema 文件位于 `../schemas/`，完整实例位于 `../examples/library/`。Narrative Beats 内嵌于 storyboard，合同 0.1 不另增第五个必须文件。Visual Brief 内嵌于 production brief，保持风格与内容设定分离。`content_strategy` 是面向真实观众的可选内容层，字段和节奏规则见 [短视频内容策划层](content-strategy.md)；它不替代 beats、shots 或音频时间轴。提示词输出遵循 [生图规范](image-generation-spec.md)，每个生成文件记录 `prompt_version`、`project_id`、任务角色、参考图用途和不可复制项。

## 单位与路径

- 宽高为像素，H.264 要求偶数。时间全部为整数帧，区间 `[start_frame, start_frame + duration_frames)`；每镜至少两帧，无空隙无重叠，顺序与 storyboard 一致。
- asset/master/reference 路径相对生产项目根；只能本地相对路径，不能 URL、绝对路径、`..` 或反斜杠。准备渲染时仅复制使用的层到 renderer/public。
- 全图层与 master 同尺寸；人物 PNG 保留全画布透明区域，不使用紧裁 bbox。中心为变换原点，x/y 为输出画布像素，scale 为统一缩放倍率。from 是镜头首帧，to 是末帧。
- z 越大越靠前且不得相同。background 必須唯一且最底层，其他层按实际遮挡排列。人物持有的纸条等刚性随身物可归到人物层；独立运动时才另拆。
- 旧合同 0.1 的线性变换路径使用 scale 1–1.3 并检查两端画布覆盖；这不是新项目的镜头运动许可。0.4 新项目默认固定机位，显式 Camera Motion 通过统一世界坐标与图层 depth 执行；局部部件关键帧与姿态切换依 [有限动画协议](limited-animation.md) 编写，实际遮挡和中间帧仍需目视复核。
- `render_profile` 只控制生图细节预算：`comic-economy` 优先清晰线条、角色身份和动作可读性，`standard` 保持均衡，`high-detail` 仅在用户明确要求时使用。它不改变题材、地域、时代或叙事目的。

## 状态与检查边界

`reference.status: planned` 可用于早期编译；正式素材准备必须 `ready` 且文件存在。`motion_plan.asset_mode: fixture` 明确允许测试图片，视频会有测试标记；切换 production 不能替代实质绘制和复核。

review 三个布尔值分别表示人工/Agent 已核对 master 对齐、遮挡背景补全、完整运动范围。程序只检查申报，不自动证明艺术质量。每镜 `notes` 写复核观察。自动 QC 不具备姿态识别或图像分割能力；精确重复哈希是底线检查。

外部图像生成不是本地脚本的一部分。Agent 负责读取 prompts/*.json、将 reference 或 master 作为图像输入、调用可用工具、保存回对应位置。没有工具时交付已编译的提示词和明确缺图清单，不能声称成片完成。
