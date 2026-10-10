# V2 Animation System

V2 的目标不是传统逐帧动画，而是把 V1 的动态漫画能力升级为可复用的 **limited animation engine**。

## 设计原则

V2 继续复用 V1 已有的 Camera、Character、Performance、Scene Graph 与音频时间轴，不破坏现有 motion_plan 0.4 项目。

新增四个明确层次：

1. **Character System**：沿用 `character-controller.mjs`，负责角色根节点、局部部件、嘴型、表情和角色能力。
2. **Pose System**：新增 `pose-controller.mjs`，负责少量关键姿势组成的 anticipation → action → hold → settle 动作。
3. **Camera System**：沿用 `camera-controller.mjs`，负责 push/pull/pan/follow 和 2.5D parallax。
4. **Effect System**：新增 `effect-controller.mjs`，统一 screen shake、flash、speed/focus/shock lines、radial burst 等夸张演出。

## 为什么使用有限动画

目标是获得“像逐帧动画”的观看体验，而不是逐帧生产成本。

一个跑动动作可以只需要：

- base pose
- anticipation pose
- action pose
- smear / motion blur
- settle

程序负责时间、位移、squash/stretch、镜头和效果；角色资产负责真正的姿势差异。

## 第一阶段数据

新增可选 `animation_system.json`，合同版本 0.1。它只描述 V2 的 pose clips 与 effects，暂不替代 `motion_plan.json`。

示例：

```json
{
  "version": "0.1",
  "project_id": "demo",
  "shots": [
    {
      "shot_id": "shot_001",
      "characters": [
        {
          "character_id": "zhouye",
          "pose_clips": [
            {
              "clip_id": "dash",
              "start_frame": 10,
              "anticipation_end_frame": 13,
              "action_end_frame": 18,
              "hold_end_frame": 24,
              "end_frame": 30,
              "base_pose": "idle",
              "action_pose": "dash",
              "smear": true,
              "translate": {"x": -160, "y": 0},
              "squash_stretch": {"x": 0.18, "y": -0.12}
            }
          ]
        }
      ],
      "effects": [
        {
          "event_id": "dash_lines",
          "effect_type": "speed_lines",
          "start_frame": 13,
          "end_frame": 20,
          "intensity": 0.9
        }
      ]
    }
  ]
}
```

## V2 里程碑

### M1 — Runtime foundation

- [x] Character System（复用 V1）
- [x] Camera System（复用 V1）
- [x] Pose System 基础运行时
- [x] Effect System 基础运行时
- [x] animation_system 0.1 Schema
- [ ] runtime tests
- [ ] renderer integration

### M2 — Character Asset Standard

每个长期角色建议最少准备：

- 5 个基础表情
- 6 个通用姿势
- closed / small / open / wide 嘴型
- open / half / closed 眼睛
- 可选 smear pose

资产必须保持统一画布、统一角色尺度与稳定身份特征。

### M3 — Animation Director

把剧本/导演意图转换为：

`dialogue beat → pose clip → camera motion → effect event → audio/subtitle timing`

Director 只生成结构化事件，Renderer 不写剧情判断。

### M4 — Reference-video complexity target

V2 第一阶段以短视频 limited animation 为上限：

- 多 pose 切换
- 快速 push-in / reaction close-up
- squash/stretch
- smear frame
- screen shake
- radial burst / speed lines
- 嘴型、眨眼、表情替换

复杂连续转身、完整骨骼动画和高帧率逐帧人体表演不作为 V2 自动化目标。
