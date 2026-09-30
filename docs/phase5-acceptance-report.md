# Phase 5 验收报告

Phase 5 已完成代码接入、自动测试、三条实际预览和旧项目实际渲染回归。开发在本阶段停止，等待验收。Phase 5 当前是本地独立改动，没有混入 Phase 4 提交。

## 1. Phase 4 commit

`569465aff5cc1816020354d353c402f4ef2d9544` — `Add scene and asset composition runtime`。

已独立 commit 并 push 到 `Dynamic-comic-video/main`。再次读取 GitHub 远端 main，返回同一个完整 hash。

## 2. 修改文件

| 文件 | 为什么修改 |
| --- | --- |
| `.gitignore` | 保留 Template 目录的可复用 PNG 测试资产，成片仍不进 Git |
| `README.md` | 增加 Mode + Template 的使用入口 |
| `assets/remotion/src/index.tsx` | 消费通用字幕呈现参数和确定性字幕选择器，没有 Mode/Template 名称分支 |
| `assets/remotion/src/runtime/character-controller.mjs` | point/raise_hand 的实际手臂旋转消费 event amplitude；缺省值仍为原来的 1 |
| `schemas/director_plan.schema.json` | 允许并验证已解析的数值 runtime_policy |
| `scripts/composition_resolver.py` | 安全构图消费可选深度强度，与实际 Parallax 使用同样参数 |
| `scripts/director.py` | 消费明确运镜策略、镜头强度、视差强度、事件强度、停顿和字幕参数；旧计划继续采用旧规则 |
| `scripts/pipeline.py` | validate/prepare 从当前 Profile + Content 重新解析 Director Plan；提前检查组合是否合法 |
| `scripts/production.py` | 将通用字幕 presentation 传给 Renderer |

完整文件清单见 `docs/phase5-file-inventory.txt`。

## 3. 新增文件

- 四个正式 Schema：`mode_manifest`、`template_manifest`、`production_profile`、`dialogue_script`。
- 四个 Mode 文件：`modes/dialogue-comedy.json`、`knowledge-explainer.json`、`motion-comic.json`、`story-animation.json`。
- `scripts/manifest_validation.py`：独立通用 Schema / Registry 检查。
- `scripts/mode_system.py`：Mode Resolver、语义导演规划、对比指标。
- `scripts/template_system.py`：Template Loader、实例化、兼容性和项目解析。
- `scripts/compose_project.py`：Content + Mode + Template 的通用创建入口。
- `scripts/make_phase5_fixture.py`：本次同内容对比样例。
- `scripts/test_mode_template.py`：22 项 Python 新测试。
- `scripts/test_mode_template_runtime.mjs`：4 项实际执行链路测试。
- `scripts/test_subtitle_runtime.mjs`：2 项字幕延留/旧行为测试。
- `assets/remotion/src/runtime/subtitle-controller.mjs`：无状态字幕选择。
- `templates/generic-room/`、`templates/generic-outdoor/`：各自 Template 和 Scene Manifest。
- `templates/_shared/base/`：角色、Capability、源项目合同和层级 PNG 测试资产；整个 Template 目录共 174 个文件、约 836 KB。
- 使用说明、验收报告和完整文件清单位于 `docs/`。

## 4. Mode Manifest Schema

顶层：`version`、`mode_id`、`description`、`policy`、`requirements`。

`policy` 包含：

| 分组 | 字段 |
| --- | --- |
| shot | max_dialogue_beats、normal_intents、emphasis_intent |
| reaction | every_n_beats、strength、hold_frames、closeup |
| camera | intent、emphasis_intent、strength、motion_every_n_shots |
| timing | line_pause_frames、emphasis_pause_before/after、reading_frames_per_character、minimum_line_frames |
| performance | explain_gesture、event_strength |
| parallax | enabled、strength |
| subtitle | font_height_ratio、emphasis_scale、hold_frames |

`requirements` 声明最少角色数、最少场景深度层、必需角色部件。字段都有范围/枚举和未知字段拒绝规则；不存在仅供 Prompt 阅读的 cinematic 标签。

## 5. Template Manifest Schema

顶层：`version`、`template_id`、`description`、`base_project`、`default_scene`、`scenes`、可选 `metadata`。

每个 `scenes[scene_id]` 声明 Scene Manifest、Character Asset Manifest、Capability Manifest 的引用、`default_bindings`、`available_props`、`shot_suggestions`。

Scene 自身继续使用 Phase 4 normalized-0-to-1 坐标、角色 Slot、Root/Face Anchor、Composition Anchor、Depth 和 Safe Bounds。Template 无导演或动画执行代码。

## 6. 四种 Mode 的规则

| Mode | 本阶段规则 |
| --- | --- |
| dialogue-comedy | 最多两句组成普通镜头；每两句筛选一次已有反应语义；22 帧反应镜头；强调单人特写；普通运镜每两镜启用一次；强调镜头强推；包袱前/后 18/30 帧停顿；事件强度 1；视差强度 0.7 |
| knowledge-explainer | 最多三句共用稳定镜头；不额外切反应镜头；解释可 point；Camera 强度 0.25，事件强度 0.55，视差强度 0.35；强调停顿 5/10 帧；字幕延留 5 帧 |
| motion-comic | 普通组镜和强调特写；Camera 固定；关闭视差；事件强度 0.35；关闭解释手势；保留局部口型和基础表演 |
| story-animation | 普通环境/中景与强调推进；Camera 强度 0.8；事件强度 0.85；视差强度 1；停顿 10/16 帧；不采用喜剧反应切镜节奏。这是最小策略实现 |

这些选择都来自 Manifest 参数，没有 Mode ID 的导演 if/else。

## 7. Mode Resolver API

`resolve_mode(mode_id, overrides=None) → validated Mode Manifest`

`direct_with_mode(script, mode, source_shot_ids, visible_characters) → Director Plan`

`plan_metrics(plan) → shot_count / average_shot_frames / reaction_shots / punchline_hold_frames / camera_emphasis`

Resolver 按内容顺序和确定性周期分组，不依赖随机数或上一帧。多人在同一组发言时使用 Two Shot。强调单独成镜。只生成语义 Intent 和帧时序，没有 Camera x/y。

## 8. Template Loader API

`load_template(template_id, scene_id=None) → manifest / selected entry / Scene / Character Assets / Capability / asset base`

`instantiate_template(template_id, project, mode_id, scene_id=None, overrides=None) → self-contained project`

`compose_project(project, script, mode, template, scene=None, overrides=None) → validated project`

调用者选择 ID 和 Content。Loader 负责解析路径、检查素材、实例化站位、复制素材和写入清晰的项目合同。

## 9. Override

`production_profile.json.overrides` 只允许覆盖 Schema 列出的 policy 叶子字段。覆盖之后重新验证完整 Mode。未知参数、越界值、非法类型、移动镜头关闭多层视差都会提前报错。

Overrides 不修改共享 Mode 文件；不能覆盖 Asset、Mode ID、Template ID 或角色 Capability 要求。

## 10. Mode 如何影响 Phase 3 Director

`dialogue_script + production_profile → resolve_mode → direct_with_mode → director_plan → compile_director_plan`。

Mode 决定镜头分组、反应是否成镜、反应强度/时长、手势、停顿和运镜意图。Phase 3 编译器把策略归一化为已有 Camera/Performance/Subtitle 数据。数值 Camera 强度缩放 zoom delta；明确的固定镜头不再被旧 emphasis/reaction 规则偷偷提升成推进。

同样四句对白，最终结果：

| 指标 | comedy | explainer |
| --- | ---: | ---: |
| 镜头数 | 5 | 2 |
| 反应镜头数 | 2 | 0 |
| 平均镜头长度 | 56 帧 / 2.33 秒 | 114 帧 / 4.75 秒 |
| 包袱前后停顿 | 48 帧 | 15 帧 |
| Camera 强调指标 | 3 | 0.25 |
| 实际移动镜头数 | 2 | 1 |

自动测试检查相对关系，没有要求必须永远是这些固定镜头数量。

## 11. Template 如何进入 Phase 4

`Template Loader → Scene Manifest + Character Asset Manifest + Capability + Slot Bindings → Scene Graph → Composition Resolver → Camera Target → Runtime`。

共享镜头从 Template 提供可见道具；单人镜头隐藏非叙事道具。角色焦点继续经过 Face/Body Anchor 到 World 坐标。Renderer 只处理图节点和计算后的变换。

`pipeline prepare` 从当前 Profile/Content 重新解析，并保存最新 Director Plan。手工遗留或过期的已保存计划不会代替当前配置。

## 12. Compatibility Validation

检查：Mode/Template 是否存在；Registry ID/Manifest ID 是否一致；场景是否属于 Template；default_scene 是否声明；Manifest 路径是否合法；PNG 是否存在、有效且尺寸正确；角色与 Capability/Asset 是否匹配；默认/项目 Slot 是否有效；角色是否可见；重复绑定；Mode 必需部件、手势所需手臂、深度层；所需 Prop；非法 Override；移动镜头/视差冲突。

上述检查在 prepare/render 之前执行。Phase 4 的 Anchor、Safe Bounds、Graph 链接/循环和素材映射检查继续执行。

## 13. 自动测试

Python 全量：**153 passed / 0 failed**，其中 Phase 5 新增 **22 项**。

JavaScript：**22 passed / 0 failed**，包含 Phase 1 Camera/Parallax、Phase 2 Character、Scene Graph/Asset Loader、4 项 Mode/Template Runtime 和 2 项 Subtitle 测试。

Runtime 测试对实际编译 payload 逐帧执行，再用乱序、跳帧、末帧优先采样比较输出；每帧检查背景覆盖；验证解释手势的实际角度、嘴部开闭、深度因子和镜头强度。

矩阵：comedy+room、explainer+room、comedy+outdoor、motion-comic+room、story-animation+outdoor 均通过编译验证；前四个组合还逐帧执行 JavaScript Runtime。

日志：`out/phase5-python-test.log`、`out/phase5-javascript-test.log`。`git diff --check` 通过。

## 14. Phase 1–4 回归

Camera、Parallax、ShotContext、Character Root/Part/Pose/Expression、Mouth、确定性、Dialogue Beat、Reaction、Pause、Intent、Director Plan、Scene/Composition、旧 0.3 sequential-comic、字幕和音频全量测试继续通过。

另实际重新渲染：

- `out/phase5-legacy-regression.mp4`：旧 0.3、144 个视频帧，H.264 + AAC，保留 supplied synthetic audio、字幕、口型和旧局部动作。
- `out/phase5-phase4-regression.mp4`：127 帧，H.264，Phase 3 Director → Phase 4 Scene → Camera/Character 再次成功。

两个渲染退出码均为 0，并检查输出媒体流和画面。

## 15. dialogue-comedy MP4

`/Users/zhou/cosmic/Dynamic-comic-video/out/phase5-dialogue-comedy.mp4`

960×540、24fps、H.264、280 帧、11.6667 秒。五镜依次为共享对白 → Lin 反应 → Lin 中景 → Bo 包袱特写推进/停顿 → Bo 反应。

## 16. knowledge-explainer MP4

`/Users/zhou/cosmic/Dynamic-comic-video/out/phase5-knowledge-explainer.mp4`

960×540、24fps、H.264、228 帧、9.5 秒。前三句维持稳定 Two Shot，Bo 解释时实际抬臂；最后一句切 Bo Medium 并使用很弱推进。

两片对白、人物及源 PNG 字节相同；没有通过换图制造 Mode 差异。这两条为无声字幕验收片。

## 17. 第二 Template

`/Users/zhou/cosmic/Dynamic-comic-video/out/phase5-generic-outdoor.mp4`

960×540、24fps、H.264、280 帧、11.6667 秒。使用同一 comedy Mode 和 Content；场景改为户外，两个 Slot 的位置/大小、场景中心、灯笼 Prop 和 Anchor 都改变；构图重新根据空间计算。没有新增户外 Core 逻辑。

已抽帧查看全部镜头及包袱镜头末端；主体脸部和头顶稳定、共享镜头容纳两人、道具可见，没有明显透明露边。解释视频另查看 point 峰值帧。全帧背景覆盖通过数值断言。

视频探测结果：`out/phase5-render-inspection.json`。抽帧证据：`out/phase5-visual-review/`。

## 18. 当前限制

- 两个 Template 是可复用测试美术，尚不是精美正式栏目资产。
- Template 能声明多场景并显式选择一个；尚不支持单条时间轴逐镜切换 Scene。
- 当前场景参考尺寸需与画布尺寸相同，继承 Phase 4 的限制。
- 表演仍使用 Phase 2 已有局部变换；point 是手臂手势，不会自动追踪具体物体；不包含 IK、骨骼、walk cycle。
- speechless 等表情继续通过现有 Capability fallback 映射到可用表情；不生成额外表情资产。
- 反应和 emphasis 依赖作者提供的语义提示；Mode 控制其使用方式，不负责自动编剧或知识判断。
- 新预览没有新增 TTS/音乐流程。旧 supplied audio 回归仍通过。
- 源面板仍作为旧合同兼容输入保存在 Template 共享 bundle 中；正式生产资产优化可以在验收后另立阶段。
- 测试源面板产生 12 条重复构图 warning，没有错误；实际镜头采用 Scene Graph 和自动构图，并已进行画面检查。

## 19. 下一阶段建议

建议先验收两种 Mode 的节奏与第二 Template 的构图，再进入下一阶段。可以开始设计固定角色栏目 Template，并保持 Core 可复用。Phase 5 已停止开发，没有自行进入 Phase 6，也没有制作最终 Classroom Template。
